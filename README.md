# Cambodia Agricultural Data Warehouse

A research prototype that integrates public agricultural, climate and development data for Cambodia into a
tested PostgreSQL star schema (Bronze, Silver, Gold), built with Python, dbt and Prefect and explored through a
Streamlit dashboard.

> **Scope.** National FAOSTAT crop statistics, World Bank indicators, CHIRPS rainfall aggregated to provinces,
> and province boundaries. **There are no provincial crop statistics here and none are inferred.**
> This is a research prototype, not an official statistical product.

## Why this exists

Real data work starts before modelling: sources arrive in different formats, units, geographic levels and time
steps. This project asks whether such sources can be integrated into one consistent, documented and tested
structure without mixing incompatible grains. It is the data-infrastructure foundation for later agricultural
forecasting work.

## What is in the warehouse

| Fact table | Grain | Source | Rows (validated run) |
|---|---|---|---|
| `fact_crop_production` | country x year x crop item | FAOSTAT | 2,658 |
| `fact_indicator_observation` | country x year x indicator | World Bank | 528 |
| `fact_climate_observation` | province x month | CHIRPS v3.0 | 25 (**one month sampled**) |

Dimensions: `dim_date`, `dim_year`, `dim_geography` (country + 25 provinces), `dim_crop` (85 FAOSTAT items),
`dim_indicator`, `dim_data_source`. Architecture diagrams are in [docs/architecture.md](docs/architecture.md).

## Validation status

Every figure comes from an executed run (full output: [reports/validation_2026-10-31.md](reports/validation_2026-10-31.md)).

| Check | Result |
|---|---|
| Unit + hygiene tests (no database) | 32 passed |
| Database integration + dashboard smoke tests | 12 passed |
| `dbt test` | 42 / 42 passed |
| Independent Gold verification (`scripts/verify_gold.py`) | 31 / 31 passed |
| Lint (`ruff`) | clean |

Not yet verified: the Docker configuration (Docker unavailable on the development machine), the GitHub Actions
workflow (first run pending), the full CHIRPS window (only one month validated), and the dashboard's visual
appearance. See [docs/limitations.md](docs/limitations.md).

## Quick start

Requirements: Python 3.11+, PostgreSQL 15+ (developed on 17), internet access. No paid services or API keys.

```bash
# 1. environments (dbt is kept apart because dbt and prefect pin conflicting dependencies)
python -m venv .venv      && .venv/Scripts/python -m pip install -r requirements.txt
python -m venv .venv-dbt  && .venv-dbt/Scripts/python -m pip install -r requirements-dbt.txt
# (use .venv/bin/ instead of .venv/Scripts/ on Linux or macOS)

# 2. database: edit the password in scripts/setup_database.sql, then run it once as the postgres superuser
psql -h localhost -U postgres -f scripts/setup_database.sql

# 3. configuration: copy the template and put the password in .env (never in .env.example)
cp .env.example .env

# 4. run the pipeline on a small sample first (one CHIRPS month)
export CADW_CHIRPS_SAMPLE_MONTHS='["2023-07"]'
python -m cadw.cli init-db
python -m cadw.cli run          # ingest -> quality gate -> Bronze -> dbt seed/run/test

# 5. verify and explore
python scripts/verify_gold.py
streamlit run app/streamlit_app.py
```

Load the full rainfall window only after the sample passes: unset `CADW_CHIRPS_SAMPLE_MONTHS` and set
`CADW_CHIRPS_START_YEAR` / `CADW_CHIRPS_END_YEAR` (each month takes roughly 4 to 14 seconds). CHIRPS rasters
are streamed and never stored.

Run `python -m cadw.cli run --sources faostat worldbank --no-dbt` to ingest selected sources only.

## Tests

```bash
pytest                       # unit + hygiene tests, no database or network
pytest -m db                 # database integration + dashboard smoke tests (needs .env)
pytest -m network            # live CHIRPS read (needs internet)
ruff check src tests app scripts
DBT_PROFILES_DIR=dbt .venv-dbt/Scripts/dbt test --project-dir dbt
```

## Repository layout

```
src/cadw/          ingestion (FAOSTAT, World Bank, CHIRPS, boundaries), quality checks, warehouse, Prefect flow, CLI
sql/               idempotent DDL for schemas, Bronze tables and audit tables
dbt/               Silver and Gold models, seeds, 8 singular + generic tests
app/               Streamlit dashboard
scripts/           database setup, independent Gold verification, data-dictionary generator
tests/             unit, hygiene, database and dashboard tests
docs/              architecture, methodology, data sources, limitations, data dictionary
reports/           validation evidence
```

## Data and licences

No data is committed; it is downloaded by the code. Source licences (FAOSTAT CC BY 4.0, World Bank CC BY 4.0,
CHIRPS public domain / CC BY 4.0, geoBoundaries ODbL 1.0) and attribution text are in
[docs/data_sources.md](docs/data_sources.md). The code is MIT licensed (see [LICENSE](LICENSE)).

## Security and privacy

Uses public data only. No National Institute of Statistics data, company data or personal data is included.
Credentials live in a git-ignored `.env`; tests fail if a password or secret pattern is tracked.

## Author

Thy Chantha: Data Science graduate in Applied Mathematics and Statistics, Institute of Technology of Cambodia.
