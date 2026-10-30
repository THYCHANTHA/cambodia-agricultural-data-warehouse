"""Database access and Bronze loading. Loads are full-refresh per source and atomic."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, Uuid, create_engine, text

from .config import PROJECT_ROOT, Settings

log = logging.getLogger(__name__)
SQL_DIR = PROJECT_ROOT / "sql"


def make_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


def apply_ddl(engine: Engine, sql_dir: Path = SQL_DIR) -> None:
    """Run every sql/*.sql file in name order. Files are idempotent."""
    for path in sorted(sql_dir.glob("*.sql")):
        log.info("applying %s", path.name)
        with engine.begin() as conn:
            conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def start_batch(engine: Engine, source_name: str, **meta) -> uuid.UUID:
    batch_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO audit.ingestion_log (batch_id, source_name, source_url, source_version,"
                " source_sha256, licence, notes) VALUES (:b, :s, :u, :v, :h, :l, :n)"
            ),
            {
                "b": batch_id,
                "s": source_name,
                "u": meta.get("source_url"),
                "v": meta.get("source_version"),
                "h": meta.get("source_sha256"),
                "l": meta.get("licence"),
                "n": meta.get("notes"),
            },
        )
    return batch_id


def finish_batch(
    engine: Engine, batch_id: uuid.UUID, *, rows: int | None, ok: bool, notes: str | None = None
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE audit.ingestion_log SET finished_at = now(), status = :st, rows_loaded = :r,"
                " notes = COALESCE(:n, notes) WHERE batch_id = :b"
            ),
            {"st": "succeeded" if ok else "failed", "r": rows, "n": notes, "b": batch_id},
        )


def load_bronze(
    engine: Engine,
    table: str,
    df: pd.DataFrame,
    batch_id: uuid.UUID,
    *,
    schema: str = "bronze",
    chunksize: int = 2000,
) -> int:
    """Replace the contents of <schema>.<table> with `df` in a single transaction (all or nothing)."""
    if df.empty:
        raise ValueError(f"refusing to load an empty frame into {schema}.{table}")
    frame = df.copy()
    frame["_batch_id"] = batch_id
    with engine.begin() as conn:
        conn.exec_driver_sql(f'TRUNCATE TABLE "{schema}"."{table}"')
        frame.to_sql(
            table,
            conn,
            schema=schema,
            if_exists="append",
            index=False,
            chunksize=chunksize,
            method="multi",
            dtype={"_batch_id": Uuid()},
        )
    return len(frame)


def store_quality_results(engine: Engine, batch_id: uuid.UUID, results) -> None:
    rows = [
        {
            "b": batch_id,
            "s": r.source,
            "c": r.check,
            "p": r.passed,
            "n": r.n_violations,
            "sev": r.severity,
            "d": r.detail,
        }
        for r in results
    ]
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO audit.data_quality_results (batch_id, source_name, check_name, passed,"
                " n_violations, severity, detail) VALUES (:b, :s, :c, :p, :n, :sev, :d)"
            ),
            rows,
        )
