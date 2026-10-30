-- Every province must have a rainfall row for every loaded month (no silently dropped provinces).
with per_month as (
  select date_key, count(*) as n_provinces from {{ ref('fact_climate_observation') }} group by date_key
)
select date_key, n_provinces
from per_month
where n_provinces <> (select count(*) from {{ ref('dim_geography') }} where geography_level = 'province')
