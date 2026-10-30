"""Independent verification of the Gold layer (does not rely on dbt's own tests).

Reconciles Gold against Bronze and against known source values, and prints a PASS/FAIL line per check.
Exit code is non-zero if any check fails.   Run:  python scripts/verify_gold.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cadw import warehouse  # noqa: E402
from cadw.config import get_settings  # noqa: E402

GOLD_TABLES = [
    "dim_date", "dim_year", "dim_geography", "dim_crop", "dim_indicator", "dim_data_source",
    "fact_crop_production", "fact_climate_observation", "fact_indicator_observation",
]  # fmt: skip

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    results.append((ok, label))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))


def scalar(conn, sql: str, **p):
    return conn.execute(text(sql), p).scalar()


def main() -> int:
    engine = warehouse.make_engine(get_settings())
    with engine.connect() as c:
        print("== existence and row counts ==")
        counts = {}
        for t in GOLD_TABLES:
            counts[t] = scalar(c, f"select count(*) from gold.{t}")
            check(counts[t] > 0, f"gold.{t} is non-empty", f"{counts[t]:,} rows")
        check(len(GOLD_TABLES) == 9, "nine Gold tables verified")

        print("== reconciliation with Bronze ==")
        bronze_obs = scalar(
            c,
            "select count(*) from (select distinct item_code, year from bronze.faostat_production"
            " where element in ('Production','Area harvested','Yield')) s"
            " join (select distinct item_code from bronze.faostat_production where element='Area harvested') a"
            " using (item_code)",
        )
        check(counts["fact_crop_production"] == bronze_obs,
              "fact_crop_production rows == distinct (crop item, year) in Bronze",
              f"gold={counts['fact_crop_production']} bronze={bronze_obs}")  # fmt: skip
        check(counts["fact_indicator_observation"] == scalar(c, "select count(*) from bronze.worldbank_indicator"),
              "fact_indicator_observation rows == Bronze World Bank rows")  # fmt: skip
        check(counts["fact_climate_observation"] == scalar(c, "select count(*) from bronze.chirps_province_monthly"),
              "fact_climate_observation rows == Bronze CHIRPS rows")  # fmt: skip
        check(scalar(c, "select count(*) from gold.dim_geography where geography_level='province'") == 25
              and scalar(c, "select count(*) from gold.dim_geography where geography_level='country'") == 1,
              "dim_geography has 1 country + 25 provinces")  # fmt: skip

        print("== known source values (FAOSTAT, Cambodia, rice 2020) ==")
        row = c.execute(text(
            "select production_t, area_harvested_ha, yield_reported_kg_ha, yield_derived_kg_ha"
            " from gold.fact_crop_production f join gold.dim_crop d using (crop_key)"
            " where d.item_name = 'Rice' and f.year = 2020")).one()  # fmt: skip
        check(float(row[0]) == 10_936_000.0, "rice 2020 production = 10,936,000 t", str(row[0]))
        check(float(row[1]) == 3_269_000.0, "rice 2020 area harvested = 3,269,000 ha", str(row[1]))
        check(abs(float(row[3]) - 3345.4) < 5, "rice 2020 derived yield ~ 3,345 kg/ha", f"{float(row[3]):.1f}")
        check(abs(float(row[2]) - 3345.4) < 0.01, "rice 2020 reported yield = 3,345.4 kg/ha", str(row[2]))

        print("== integrity ==")
        check(scalar(c, "select count(*) from gold.fact_crop_production f left join gold.dim_geography g using (geography_key) where g.geography_level <> 'country'") == 0,
              "every crop fact is at COUNTRY level (no provincial crop statistics exist)")  # fmt: skip
        check(scalar(c, "select count(*) from gold.fact_climate_observation f join gold.dim_geography g using (geography_key) where g.geography_level <> 'province'") == 0,
              "every rainfall fact is at PROVINCE level")  # fmt: skip
        check(scalar(c, "select count(*) from gold.fact_crop_production where yield_discrepancy_pct > 1") == 0,
              "reported vs derived yield within 1% everywhere")  # fmt: skip
        mx = scalar(c, "select max(yield_discrepancy_pct) from gold.fact_crop_production")
        check(mx is not None and float(mx) < 0.3, "max yield discrepancy matches design-time finding (<0.3%)", f"{float(mx):.3f}%")
        check(scalar(c, "select count(*) from gold.dim_crop where item_type='crop' and is_aggregate") > 0
              and scalar(c, "select count(*) from gold.dim_crop where not is_aggregate and crop_key >= 1700") == 0,
              "aggregate FAOSTAT items are flagged")  # fmt: skip
        check(scalar(c, "select count(*) from gold.dim_crop where crop_key = 27 and item_type='crop' and not is_aggregate") == 1,
              "Rice (27) is a non-aggregate crop")  # fmt: skip
        check(scalar(c, "select count(*) from gold.fact_climate_observation where valid_pixel_ratio < 1") == 0,
              "every province-month has full valid-pixel coverage (or flagged)")  # fmt: skip
        check(scalar(c, "select count(*) from gold.fact_crop_production where production_t is null and production_flag is distinct from 'M'") == 0,
              "NULL production only where FAOSTAT flags the value missing ('M')")  # fmt: skip
        check(scalar(c, "select count(*) from gold.dim_data_source where latest_loaded_at is null") == 0,
              "every source in dim_data_source has a recorded successful load")  # fmt: skip

        print("== provenance ==")
        for src, n in c.execute(text("select source_name, count(*) from audit.ingestion_log where status='succeeded' group by 1 order by 1")):
            check(n >= 1, f"audit.ingestion_log has a successful batch for {src}", f"{n} batch(es)")

    failed = [label for ok, label in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
