{{ config(post_hook="alter table {{ this }} add primary key (geography_key, date_key)") }}
-- Grain: one row per province x month. Source: CHIRPS v3.0 (0.05 degree), aggregated to ADM1.
-- Values are the spatial mean/min/max of pixel monthly totals (mm). valid_pixel_ratio exposes coverage.
select
    md5('province|' || c.province_id)   as geography_key,
    (c.year * 100 + c.month)            as date_key,
    'chirps_province_monthly'           as source_key,
    c.precip_mean_mm,
    c.precip_min_mm,
    c.precip_max_mm,
    c.n_pixels,
    c.n_valid_pixels,
    c.valid_pixel_ratio,
    c.mask_method
from {{ ref('stg_chirps_monthly') }} c
