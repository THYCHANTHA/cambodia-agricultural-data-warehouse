-- Grain: one row per World Bank indicator.
select
    indicator_code      as indicator_key,
    max(indicator_name) as indicator_name,
    max(unit)           as unit
from {{ ref('stg_worldbank_indicator') }}
group by indicator_code
