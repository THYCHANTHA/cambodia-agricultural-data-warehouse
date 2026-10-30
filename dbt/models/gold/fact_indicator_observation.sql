{{ config(post_hook="alter table {{ this }} add primary key (geography_key, indicator_key, year)") }}
-- Grain: one row per country x year x World Bank indicator (missing observations kept, value NULL).
select
    md5('country|' || country_iso3)     as geography_key,
    indicator_code                      as indicator_key,
    year,
    'worldbank_indicator'               as source_key,
    value,
    is_missing,
    obs_status
from {{ ref('stg_worldbank_indicator') }}
