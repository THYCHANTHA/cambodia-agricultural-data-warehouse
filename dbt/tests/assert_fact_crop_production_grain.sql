-- Grain uniqueness: one row per country x year x crop.
select crop_key, year, count(*) as n
from {{ ref('fact_crop_production') }}
group by crop_key, year
having count(*) > 1
