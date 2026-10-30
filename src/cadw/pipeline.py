"""End-to-end pipeline: ingest -> quality gate -> Bronze load -> (dbt) Silver/Gold -> dbt tests.

Each source is an independent Prefect task with retries. A source that fails its *error*-severity
quality checks is not loaded, and the flow fails visibly rather than publishing partial data.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from prefect import flow, get_run_logger, task

from . import warehouse
from .config import PROJECT_ROOT, Settings, get_settings
from .ingestion import boundaries, chirps, faostat, worldbank
from .ingestion.http import download_file
from .quality import checks

log = logging.getLogger(__name__)
DBT_DIR = PROJECT_ROOT / "dbt"


def _gate(engine, batch_id, results) -> None:
    warehouse.store_quality_results(engine, batch_id, results)
    ok, summary = checks.summarise(results)
    get_run_logger().info(summary)
    if not ok:
        warehouse.finish_batch(engine, batch_id, rows=None, ok=False, notes=summary[:2000])
        raise RuntimeError(f"quality gate failed:\n{summary}")


@task(retries=2, retry_delay_seconds=30)
def ingest_faostat(settings: Settings) -> int:
    engine = warehouse.make_engine(settings)
    zip_path = settings.raw_dir / "faostat" / "crops_livestock.zip"
    info = download_file(faostat.FAOSTAT_URL, zip_path)
    batch = warehouse.start_batch(
        engine,
        "faostat_production",
        source_url=faostat.FAOSTAT_URL,
        source_sha256=info["sha256"],
        licence="see docs/data_sources.md",
    )
    try:
        df = faostat.to_bronze(faostat.read_country_from_zip(zip_path, settings.country_m49))
        flags = faostat.read_lookup(zip_path, "Flags.csv")
        flags.columns = ["flag", "description"]
        results = [
            checks.not_empty(df, "faostat_production"),
            checks.no_duplicate_keys(df, "faostat_production", ["item_code", "element_code", "year"]),
            checks.year_window(df, "faostat_production", "year", 1961, 2100),
            checks.missing_share(df, "faostat_production", "value", 0.10),
        ]
        _gate(engine, batch, results)
        n = warehouse.load_bronze(engine, "faostat_production", df, batch)
        warehouse.load_bronze(engine, "faostat_flags", flags, batch)
        warehouse.finish_batch(engine, batch, rows=n, ok=True)
        return n
    except Exception as exc:
        warehouse.finish_batch(engine, batch, rows=None, ok=False, notes=str(exc)[:2000])
        raise


@task(retries=2, retry_delay_seconds=30)
def ingest_worldbank(settings: Settings) -> int:
    engine = warehouse.make_engine(settings)
    batch = warehouse.start_batch(
        engine,
        "worldbank_indicator",
        source_url="https://api.worldbank.org/v2/",
        licence="CC BY 4.0",
    )
    try:
        df, stamps = worldbank.fetch_indicators(
            settings.country_iso3,
            settings.worldbank_indicators,
            timeout=settings.http_timeout_s,
            retries=settings.http_retries,
        )
        results = [
            checks.not_empty(df, "worldbank_indicator"),
            checks.no_duplicate_keys(df, "worldbank_indicator", ["indicator_code", "year"]),
            checks.year_window(df, "worldbank_indicator", "year", 1960, 2100),
            checks.missing_share(df, "worldbank_indicator", "value", 0.50),
        ]
        _gate(engine, batch, results)
        n = warehouse.load_bronze(engine, "worldbank_indicator", df, batch)
        warehouse.finish_batch(
            engine, batch, rows=n, ok=True, notes=f"source lastupdated: {sorted(set(stamps.values()))}"
        )
        return n
    except Exception as exc:
        warehouse.finish_batch(engine, batch, rows=None, ok=False, notes=str(exc)[:2000])
        raise


@task(retries=2, retry_delay_seconds=30)
def ingest_boundaries(settings: Settings) -> int:
    engine = warehouse.make_engine(settings)
    path, info = boundaries.download_adm1(settings.country_iso3, settings.raw_dir)
    batch = warehouse.start_batch(
        engine,
        "geoboundaries_adm1",
        source_url=info["url"],
        source_sha256=info["sha256"],
        licence=info["licence"],
        source_version=str(info["year"]),
    )
    try:
        df = boundaries.load_adm1_table(path)
        results = [
            checks.not_empty(df, "geoboundaries_adm1"),
            checks.no_duplicate_keys(df, "geoboundaries_adm1", ["shape_id"]),
            checks.expected_count(df, "geoboundaries_adm1", 25, "provinces"),
        ]
        _gate(engine, batch, results)
        n = warehouse.load_bronze(engine, "geoboundaries_adm1", df, batch)
        warehouse.finish_batch(engine, batch, rows=n, ok=True)
        return n
    except Exception as exc:
        warehouse.finish_batch(engine, batch, rows=None, ok=False, notes=str(exc)[:2000])
        raise


@task(retries=1, retry_delay_seconds=60)
def ingest_chirps(settings: Settings, boundary_rows: int) -> int:
    engine = warehouse.make_engine(settings)
    batch = warehouse.start_batch(
        engine,
        "chirps_province_monthly",
        source_url=settings.chirps_base_url,
        licence="see docs/data_sources.md",
        notes=f"window {settings.chirps_start_year}-{settings.chirps_end_year}",
    )
    try:
        import pandas as pd

        with engine.connect() as conn:
            bdf = pd.read_sql("select shape_id, geometry_geojson from bronze.geoboundaries_adm1", conn)
        geoms = chirps.province_geometries(bdf)
        df = chirps.ingest(
            settings.chirps_base_url, settings.chirps_start_year, settings.chirps_end_year, geoms
        )
        failures = df.attrs.get("failures", [])
        results = [
            checks.not_empty(df, "chirps_province_monthly"),
            checks.no_duplicate_keys(df, "chirps_province_monthly", ["province_key", "year", "month"]),
            checks.value_range(df, "chirps_province_monthly", "precip_mean_mm", 0, 2500),
            checks.chirps_completeness(
                df, len(geoms), settings.chirps_start_year, settings.chirps_end_year, failures
            ),
        ]
        _gate(engine, batch, results)
        n = warehouse.load_bronze(engine, "chirps_province_monthly", df, batch)
        warehouse.finish_batch(engine, batch, rows=n, ok=True)
        return n
    except Exception as exc:
        warehouse.finish_batch(engine, batch, rows=None, ok=False, notes=str(exc)[:2000])
        raise


@task
def run_dbt(command: list[str]) -> None:
    """Run dbt via the executable named in CADW_DBT_BIN (dbt lives in its own virtualenv)."""
    exe = os.environ.get("CADW_DBT_BIN", "dbt")
    env = {**os.environ, "DBT_PROFILES_DIR": str(DBT_DIR)}
    proc = subprocess.run(
        [exe, *command, "--project-dir", str(DBT_DIR)], env=env, capture_output=True, text=True
    )
    get_run_logger().info(proc.stdout[-4000:])
    if proc.returncode != 0:
        raise RuntimeError(f"dbt {' '.join(command)} failed:\n{proc.stdout[-3000:]}\n{proc.stderr[-1000:]}")


@flow(name="cambodia-agricultural-warehouse")
def run_pipeline(settings: Settings | None = None, skip_chirps: bool = False) -> None:
    settings = settings or get_settings()
    engine = warehouse.make_engine(settings)
    warehouse.apply_ddl(engine)

    ingest_faostat(settings)
    ingest_worldbank(settings)
    n_boundaries = ingest_boundaries(settings)
    if not skip_chirps:
        ingest_chirps(settings, n_boundaries)

    run_dbt(["seed"])
    run_dbt(["run"])
    run_dbt(["test"])


def apply_only(settings: Settings | None = None) -> Path:
    """Create schemas and Bronze tables only (used by `cadw init-db`)."""
    settings = settings or get_settings()
    warehouse.apply_ddl(warehouse.make_engine(settings))
    return warehouse.SQL_DIR
