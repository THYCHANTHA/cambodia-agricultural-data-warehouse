-- Silver: one row per indicator-year. Null observations are retained with is_missing = true.
select
    indicator_code,
    indicator_name,
    country_iso3,
    year::int                    as year,
    value,
    (value is null)              as is_missing,
    nullif(unit, '')             as unit,
    nullif(obs_status, '')       as obs_status,
    _batch_id,
    _loaded_at
from {{ source('bronze', 'worldbank_indicator') }}
where year ~ '^[0-9]{4}$'
