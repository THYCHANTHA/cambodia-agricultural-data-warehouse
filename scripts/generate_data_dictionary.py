"""Generate docs/data_dictionary.md from the live database schema (column names and types are
read from information_schema, so the document cannot drift from the real tables).

Table grain/description text is maintained here. Run:  python scripts/generate_data_dictionary.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cadw import warehouse  # noqa: E402
from cadw.config import get_settings  # noqa: E402

TABLES: dict[str, dict[str, str]] = {
    "gold.dim_date": {"grain": "one row per calendar month", "note": "rainy_season_approx is a coarse May-Oct climatological label, not an observation."},
    "gold.dim_year": {"grain": "one row per calendar year (from 1960)", "note": "Annual facts reference this dimension."},
    "gold.dim_geography": {"grain": "one row per geographic unit (country, province)", "note": "Hash surrogate keys; hierarchy via parent_geography_key. No SCD: one boundary vintage only."},
    "gold.dim_crop": {"grain": "one row per FAOSTAT item", "note": "item_type is derived from reported elements; is_aggregate marks FAOSTAT group items (code >= 1700) that must not be summed with their members."},
    "gold.dim_indicator": {"grain": "one row per World Bank indicator", "note": ""},
    "gold.dim_data_source": {"grain": "one row per source system", "note": "Latest successful load attached from audit.ingestion_log."},
    "gold.fact_crop_production": {"grain": "country x year x crop item (NATIONAL only)", "note": "FAOSTAT has no provincial data. yield_derived_kg_ha = production_t * 1000 / area_harvested_ha is a cross-check of the reported yield."},
    "gold.fact_climate_observation": {"grain": "province x month", "note": "CHIRPS v3.0 (0.05 deg) aggregated to ADM1; valid_pixel_ratio exposes coverage."},
    "gold.fact_indicator_observation": {"grain": "country x year x indicator", "note": "Missing observations are kept with value NULL."},
    "silver.stg_faostat_production": {"grain": "item x element x year (typed, de-duplicated, unit-standardised)", "note": "Blank source values stay NULL; never imputed."},
    "silver.stg_worldbank_indicator": {"grain": "indicator x year", "note": ""},
    "silver.stg_geography": {"grain": "province", "note": ""},
    "silver.stg_chirps_monthly": {"grain": "province x month", "note": ""},
    "silver.stg_faostat_flags": {"grain": "FAOSTAT flag code", "note": ""},
    "audit.ingestion_log": {"grain": "one row per ingestion batch per source", "note": "Provenance: URL, checksum, version, licence, status."},
    "audit.data_quality_results": {"grain": "one row per check per batch", "note": ""},
}


def main() -> None:
    engine = warehouse.make_engine(get_settings())
    out = ["# Data dictionary", "", "Generated from the live PostgreSQL schema by `scripts/generate_data_dictionary.py`.", ""]
    with engine.connect() as c:
        for qualified, meta in TABLES.items():
            schema, table = qualified.split(".")
            n = c.execute(text(f"select count(*) from {qualified}")).scalar()
            cols = c.execute(
                text(
                    "select column_name, data_type, is_nullable from information_schema.columns"
                    " where table_schema = :s and table_name = :t order by ordinal_position"
                ),
                {"s": schema, "t": table},
            ).all()
            out += [f"## `{qualified}`", "", f"**Grain:** {meta['grain']}  ", f"**Rows at generation time:** {n:,}  "]
            if meta["note"]:
                out.append(f"**Note:** {meta['note']}  ")
            out += ["", "| Column | Type | Nullable |", "|---|---|---|"]
            out += [f"| `{name}` | {dtype} | {nullable} |" for name, dtype, nullable in cols]
            out.append("")
    (ROOT / "docs" / "data_dictionary.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote docs/data_dictionary.md ({len(TABLES)} tables)")


if __name__ == "__main__":
    main()
