-- Silver: province-month rainfall. Rows with no valid pixels are kept with NULL values.
select
    province_key                                         as province_id,
    make_date(year, month, 1)                            as month_start,
    year, month,
    precip_mean_mm, precip_min_mm, precip_max_mm,
    n_pixels, n_valid_pixels,
    round(n_valid_pixels::numeric / nullif(n_pixels, 0), 4) as valid_pixel_ratio,
    mask_method,
    _batch_id,
    _loaded_at
from {{ source('bronze', 'chirps_province_monthly') }}
