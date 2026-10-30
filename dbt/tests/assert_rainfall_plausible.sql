-- Monthly CHIRPS means must be physically plausible: 0 to 2500 mm per month.
select geography_key, date_key, precip_mean_mm
from {{ ref('fact_climate_observation') }}
where precip_mean_mm < 0 or precip_mean_mm > 2500
