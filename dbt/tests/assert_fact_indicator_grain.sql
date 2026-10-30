-- Grain uniqueness: one row per country x year x indicator.
select indicator_key, year, count(*) as n
from {{ ref('fact_indicator_observation') }}
group by indicator_key, year
having count(*) > 1
