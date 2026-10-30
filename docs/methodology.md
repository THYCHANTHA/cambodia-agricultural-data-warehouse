# Methodology

## 1. Research problem

Public agricultural, climate and development information about Cambodia is spread across sources with
different formats, units, geographic levels and time steps. The question addressed here is an engineering one:
**can these sources be integrated into one consistent, documented, tested analytical structure without
mixing incompatible grains?**

## 2. Approach

A medallion pipeline (Bronze, Silver, Gold) loading a PostgreSQL star schema.

1. **Acquire** each source with retries and record provenance (URL, SHA-256 of downloaded files, source
   version stamp, licence) in `audit.ingestion_log`.
2. **Validate at source level** before loading (section 4). Failing an error-severity check stops the load.
3. **Load Bronze** as received, plus lineage columns, in one all-or-nothing transaction.
4. **Transform to Silver** with dbt: cast types, de-duplicate, standardise units.
5. **Build Gold** with dbt: dimensions and facts with explicit grain and primary keys.
6. **Test** with dbt (42 tests) and with an independent script that reconciles Gold against Bronze and known
   source values (`scripts/verify_gold.py`, 31 checks).

## 3. Transformations

### 3.1 Unit standardisation
A seed table (`dbt/seeds/faostat_unit_map.csv`) maps every source unit to a canonical unit and factor, for
example `1000 An` to `animals` x 1000. After Silver, crop production is in tonnes, area in hectares and yield
in kg/ha. A dbt test fails if any crop measure appears in another unit.

### 3.2 Yield
Reported yield is kept as published. A derived value is computed as a cross-check:

yield_derived (kg/ha) = production (t) x 1000 / area harvested (ha)

`yield_discrepancy_pct = |yield_derived - yield_reported| / yield_reported x 100`.

Before choosing a tolerance, the discrepancy was measured on the real data: over 2,359 crop-year
observations with all three values present, the median was 0.001%, the 99th percentile 0.13% and the
maximum 0.27% (consistent with rounding of published figures). The dbt test therefore fails any row above
**1%**, a threshold that is loose against rounding but would catch a unit error (a factor of 10 or 1000).

### 3.3 Rainfall aggregation
For a province with pixel set P (pixels whose centre lies inside the province polygon) and monthly pixel
totals x_i (mm), valid pixels V = {i in P : x_i is not NoData and x_i >= 0}:

precip_mean_mm = (1 / |V|) x sum of x_i for i in V

Minimum and maximum over V are also stored, with |P| (`n_pixels`) and |V| (`n_valid_pixels`) so coverage is
visible. If no pixel centre lies inside a province, all pixels touched by the polygon are used and
`mask_method = all_touched` records the fallback. The mean is unweighted; it ignores the small variation in
pixel area with latitude across Cambodia.

### 3.4 Geography
Provinces are identified by the geoBoundaries `shapeID`. Surrogate keys are
`md5(level || '|' || natural_id)`. Country-level facts attach to the country row and province-level facts to
province rows; the hierarchy is available through `parent_geography_key`.

## 4. Data-quality rules

| Source | Check | Severity |
|---|---|---|
| All | Non-empty | error |
| FAOSTAT | No duplicate (item, element, year); year in 1961-2100 | error |
| FAOSTAT | Blank `Value` share <= 10% | warning |
| World Bank | No duplicate (indicator, year); year in 1960-2100 | error |
| World Bank | Null share <= 50% | warning |
| Boundaries | Exactly 25 provinces; unique ids | error |
| CHIRPS | No duplicate (province, year, month); mean in 0-2,500 mm; completeness = provinces x months with no failed month | error |

Missing values are warnings because official statistics legitimately contain gaps. Results are stored per
batch in `audit.data_quality_results`.

## 5. Validation evidence

All figures are from executed runs on 2026-10-31 (see `reports/validation_2026-10-31.md`).

| Check | Result |
|---|---|
| Python unit and hygiene tests | 32 passed |
| Database integration tests | 4 passed |
| Dashboard page smoke tests | 8 passed |
| `dbt test` | 42 of 42 passed |
| `scripts/verify_gold.py` | 31 of 31 passed |
| FAOSTAT Cambodia rows loaded | 12,621 (matches an independent pre-count) |
| World Bank rows loaded | 528 (8 indicators x 66 years) |
| Provinces loaded | 25 |
| CHIRPS | 1 month (2023-07), 25 province rows, 100% valid pixels |

Defects found only by executing against a real database, and fixed:

1. Batch ids were written as text into a `uuid` column, so every Bronze insert failed. The failed
   transaction left Bronze empty (atomicity confirmed). Fixed, with regression tests.
2. `dim_year` started in 1961 but the World Bank series starts in 1960, so 8 facts had no matching year. The
   dimension was corrected; the test was not weakened.

## 6. Reproducibility

See `README.md`. Random seeds are not used because the pipeline is deterministic. Data are downloaded by
scripts and never committed; checksums of downloaded files are stored in `audit.ingestion_log`.

## 7. Limitations

See `docs/limitations.md`.
