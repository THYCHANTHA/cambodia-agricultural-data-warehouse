# Data dictionary

Generated from the live PostgreSQL schema by `scripts/generate_data_dictionary.py`.

## `gold.dim_date`

**Grain:** one row per calendar month  
**Rows at generation time:** 792  
**Note:** rainy_season_approx is a coarse May-Oct climatological label, not an observation.  

| Column | Type | Nullable |
|---|---|---|
| `date_key` | integer | YES |
| `month_start` | date | YES |
| `year` | integer | YES |
| `month` | integer | YES |
| `quarter` | integer | YES |
| `month_name` | text | YES |
| `rainy_season_approx` | boolean | YES |

## `gold.dim_year`

**Grain:** one row per calendar year (from 1960)  
**Rows at generation time:** 67  
**Note:** Annual facts reference this dimension.  

| Column | Type | Nullable |
|---|---|---|
| `year` | integer | YES |
| `decade` | integer | YES |

## `gold.dim_geography`

**Grain:** one row per geographic unit (country, province)  
**Rows at generation time:** 26  
**Note:** Hash surrogate keys; hierarchy via parent_geography_key. No SCD: one boundary vintage only.  

| Column | Type | Nullable |
|---|---|---|
| `geography_key` | text | YES |
| `parent_geography_key` | text | YES |
| `geography_level` | text | YES |
| `natural_id` | text | YES |
| `geography_name` | text | YES |
| `country_iso3` | text | YES |
| `province_iso` | text | YES |

## `gold.dim_crop`

**Grain:** one row per FAOSTAT item  
**Rows at generation time:** 85  
**Note:** item_type is derived from reported elements; is_aggregate marks FAOSTAT group items (code >= 1700) that must not be summed with their members.  

| Column | Type | Nullable |
|---|---|---|
| `crop_key` | integer | YES |
| `item_name` | text | YES |
| `cpc_code` | text | YES |
| `item_type` | text | YES |
| `is_aggregate` | boolean | YES |

## `gold.dim_indicator`

**Grain:** one row per World Bank indicator  
**Rows at generation time:** 8  

| Column | Type | Nullable |
|---|---|---|
| `indicator_key` | text | YES |
| `indicator_name` | text | YES |
| `unit` | text | YES |

## `gold.dim_data_source`

**Grain:** one row per source system  
**Rows at generation time:** 4  
**Note:** Latest successful load attached from audit.ingestion_log.  

| Column | Type | Nullable |
|---|---|---|
| `source_key` | text | YES |
| `publisher` | text | YES |
| `description` | text | YES |
| `url` | text | YES |
| `licence_summary` | text | YES |
| `native_grain` | text | YES |
| `latest_batch_id` | uuid | YES |
| `latest_loaded_at` | timestamp with time zone | YES |
| `source_version` | text | YES |
| `source_sha256` | text | YES |

## `gold.fact_crop_production`

**Grain:** country x year x crop item (NATIONAL only)  
**Rows at generation time:** 2,658  
**Note:** FAOSTAT has no provincial data. yield_derived_kg_ha = production_t * 1000 / area_harvested_ha is a cross-check of the reported yield.  

| Column | Type | Nullable |
|---|---|---|
| `geography_key` | text | YES |
| `crop_key` | integer | YES |
| `year` | integer | YES |
| `source_key` | text | YES |
| `production_t` | numeric | YES |
| `area_harvested_ha` | numeric | YES |
| `yield_reported_kg_ha` | numeric | YES |
| `yield_derived_kg_ha` | numeric | YES |
| `yield_discrepancy_pct` | numeric | YES |
| `production_flag` | text | YES |
| `area_flag` | text | YES |
| `yield_flag` | text | YES |

## `gold.fact_climate_observation`

**Grain:** province x month  
**Rows at generation time:** 25  
**Note:** CHIRPS v3.0 (0.05 deg) aggregated to ADM1; valid_pixel_ratio exposes coverage.  

| Column | Type | Nullable |
|---|---|---|
| `geography_key` | text | YES |
| `date_key` | integer | YES |
| `source_key` | text | YES |
| `precip_mean_mm` | double precision | YES |
| `precip_min_mm` | double precision | YES |
| `precip_max_mm` | double precision | YES |
| `n_pixels` | integer | YES |
| `n_valid_pixels` | integer | YES |
| `valid_pixel_ratio` | numeric | YES |
| `mask_method` | text | YES |

## `gold.fact_indicator_observation`

**Grain:** country x year x indicator  
**Rows at generation time:** 528  
**Note:** Missing observations are kept with value NULL.  

| Column | Type | Nullable |
|---|---|---|
| `geography_key` | text | YES |
| `indicator_key` | text | YES |
| `year` | integer | YES |
| `source_key` | text | YES |
| `value` | double precision | YES |
| `is_missing` | boolean | YES |
| `obs_status` | text | YES |

## `silver.stg_faostat_production`

**Grain:** item x element x year (typed, de-duplicated, unit-standardised)  
**Rows at generation time:** 12,621  
**Note:** Blank source values stay NULL; never imputed.  

| Column | Type | Nullable |
|---|---|---|
| `item_code` | integer | YES |
| `item_code_cpc` | text | YES |
| `item_name` | text | YES |
| `element_code` | integer | YES |
| `element_name` | text | YES |
| `year` | integer | YES |
| `unit` | text | YES |
| `value` | numeric | YES |
| `source_unit` | text | YES |
| `flag` | text | YES |
| `is_missing` | boolean | YES |
| `_batch_id` | uuid | YES |
| `_loaded_at` | timestamp with time zone | YES |

## `silver.stg_worldbank_indicator`

**Grain:** indicator x year  
**Rows at generation time:** 528  

| Column | Type | Nullable |
|---|---|---|
| `indicator_code` | text | YES |
| `indicator_name` | text | YES |
| `country_iso3` | text | YES |
| `year` | integer | YES |
| `value` | double precision | YES |
| `is_missing` | boolean | YES |
| `unit` | text | YES |
| `obs_status` | text | YES |
| `_batch_id` | uuid | YES |
| `_loaded_at` | timestamp with time zone | YES |

## `silver.stg_geography`

**Grain:** province  
**Rows at generation time:** 25  

| Column | Type | Nullable |
|---|---|---|
| `province_id` | text | YES |
| `province_name` | text | YES |
| `province_iso` | text | YES |
| `country_iso3` | text | YES |
| `geometry_geojson` | text | YES |
| `_batch_id` | uuid | YES |
| `_loaded_at` | timestamp with time zone | YES |

## `silver.stg_chirps_monthly`

**Grain:** province x month  
**Rows at generation time:** 25  

| Column | Type | Nullable |
|---|---|---|
| `province_id` | text | YES |
| `month_start` | date | YES |
| `year` | integer | YES |
| `month` | integer | YES |
| `precip_mean_mm` | double precision | YES |
| `precip_min_mm` | double precision | YES |
| `precip_max_mm` | double precision | YES |
| `n_pixels` | integer | YES |
| `n_valid_pixels` | integer | YES |
| `valid_pixel_ratio` | numeric | YES |
| `mask_method` | text | YES |
| `_batch_id` | uuid | YES |
| `_loaded_at` | timestamp with time zone | YES |

## `silver.stg_faostat_flags`

**Grain:** FAOSTAT flag code  
**Rows at generation time:** 5  

| Column | Type | Nullable |
|---|---|---|
| `flag` | text | YES |
| `description` | text | YES |

## `audit.ingestion_log`

**Grain:** one row per ingestion batch per source  
**Rows at generation time:** 7  
**Note:** Provenance: URL, checksum, version, licence, status.  

| Column | Type | Nullable |
|---|---|---|
| `batch_id` | uuid | NO |
| `source_name` | text | NO |
| `started_at` | timestamp with time zone | NO |
| `finished_at` | timestamp with time zone | YES |
| `status` | text | NO |
| `rows_loaded` | bigint | YES |
| `source_url` | text | YES |
| `source_version` | text | YES |
| `source_sha256` | text | YES |
| `licence` | text | YES |
| `notes` | text | YES |

## `audit.data_quality_results`

**Grain:** one row per check per batch  
**Rows at generation time:** 24  

| Column | Type | Nullable |
|---|---|---|
| `id` | bigint | NO |
| `batch_id` | uuid | NO |
| `source_name` | text | NO |
| `check_name` | text | NO |
| `passed` | boolean | NO |
| `n_violations` | bigint | NO |
| `severity` | text | NO |
| `detail` | text | YES |
| `checked_at` | timestamp with time zone | NO |
