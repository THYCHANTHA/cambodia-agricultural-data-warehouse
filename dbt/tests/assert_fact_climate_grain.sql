-- Grain uniqueness: one row per province x month.
select geography_key, date_key, count(*) as n
from {{ ref('fact_climate_observation') }}
group by geography_key, date_key
having count(*) > 1
