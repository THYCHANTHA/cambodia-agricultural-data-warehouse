# Limitations

This is a research prototype, not an official statistical product.

## Data

1. **National-only crop statistics.** FAOSTAT is national. There is no provincial crop production, area or
   yield here, and none is estimated or inferred from national figures. Questions such as "which province
   has the highest rice yield?" cannot be answered with this warehouse.
2. **Rainfall is a satellite-gauge estimate** (CHIRPS), not a station measurement. Province values are the
   mean of 0.05 degree pixels whose centres fall inside the province boundary. A province smaller than one
   pixel falls back to every pixel it touches (`mask_method = all_touched`); none did in the validated month.
3. **Rainfall coverage is a sample.** Validation was run on one month (July 2023). Any rainfall analysis
   requires the wider window to be loaded and validated first (see `BUILD_STATUS.md` for the current state).
4. **Boundary vintage is 2017.** Province boundaries may differ from current administrative boundaries.
5. **No temperature or other covariates** are integrated yet.
6. **Missing values are preserved.** FAOSTAT blanks (flag `M`) and World Bank nulls stay NULL; nothing is imputed.
   FAOSTAT also contains values estimated or imputed by FAO itself (flags `E`, `I`); these are kept and flagged.
7. **Aggregate FAOSTAT items** (codes 1700 and above) overlap with individual crops. They are flagged and must
   not be summed with them.

## Engineering

1. **Referential integrity is tested, not declared.** Primary keys are enforced by the database; foreign keys
   are checked by dbt `relationships` tests rather than constraints, so dbt can rebuild tables freely.
2. **No incremental loads.** Each source is fully refreshed per run. That is simple and safe at this size
   (12,621 FAOSTAT rows, 528 World Bank rows) but would not scale to large fact tables.
3. **No slowly changing dimensions.** Only one boundary vintage exists.
4. **Docker files are unverified.** Docker is not installed on the development machine, so the container
   configuration has not been built or run.
5. **CI is unverified until the first GitHub run.** The workflow could not be executed locally.
6. **The dashboard has been smoke-tested, not visually reviewed.** Automated tests confirm every page renders
   against the live database without error; layout and appearance have not been reviewed in a browser.
7. **Local development database.** The setup scripts target a local PostgreSQL instance and are not
   hardened for production use.

## Scope

The warehouse supports exploration and later modelling work. It is not suited to official reporting,
policy decisions, or operational forecasting.
