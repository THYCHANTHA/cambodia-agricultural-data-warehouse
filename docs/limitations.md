# Limitations

This is a research prototype, not an official statistical product.

## Data

1. **National-only crop statistics.** FAOSTAT is national. There is no provincial crop production, area or
   yield here, and none is estimated or inferred from national figures. Questions such as "which province
   has the highest rice yield?" cannot be answered with this warehouse.
2. **Rainfall is a satellite-gauge estimate** (CHIRPS), not a station measurement. Province values are the
   mean of 0.05 degree pixels whose centres fall inside the province boundary. A province smaller than one
   pixel falls back to every pixel it touches (`mask_method = all_touched`); none did in the validated month.
3. **Rainfall coverage is a sample.** Only **one month (July 2023) has been loaded and validated**. No
   historical rainfall analysis is claimed. Any such analysis requires the wider window to be loaded and
   validated first; the dashboard shows a warning while fewer than 12 months are loaded.
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
4. **Docker files are untested.** Docker is not installed on the development machine, so the container
   configuration has never been built or run.
5. **CI has never run.** The first GitHub Actions run could not start because the owner's GitHub account was locked for a billing issue (reported by GitHub as the reason the job was not started). The workflow is therefore untested on GitHub; the equivalent checks were run locally. It also still has to exercise `scripts/setup_database.sql` for the first time.
6. **Dashboard review covers desktop only.** Automated tests confirm every page renders against the live
   database, and a visual review of all six pages on desktop was done in a headless browser (it found and fixed
   unreadable dark-mode text, raw axis labels and a missing sample warning). Mobile layout was not reviewed.
7. **Local development database.** The setup scripts target a local PostgreSQL instance and are not
   hardened for production use.

## Scope

The warehouse supports exploration and later modelling work. It is not suited to official reporting,
policy decisions, or operational forecasting.
