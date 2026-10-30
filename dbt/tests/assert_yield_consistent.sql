-- Reported yield must agree with production/area. Tolerance 1%: the largest deviation observed in
-- the real FAOSTAT Cambodia data at design time was 0.27% (rounding of published values).
select crop_key, year, yield_discrepancy_pct
from {{ ref('fact_crop_production') }}
where yield_discrepancy_pct > 1
