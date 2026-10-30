-- Grain: one row per calendar month. Monthly facts (CHIRPS) reference this dimension.
-- rainy_season_approx is a coarse climatological label (southwest monsoon, May-Oct), not an observation.
select
    (extract(year from d)::int * 100 + extract(month from d)::int)  as date_key,
    d::date                                                         as month_start,
    extract(year from d)::int                                       as year,
    extract(month from d)::int                                      as month,
    extract(quarter from d)::int                                    as quarter,
    to_char(d, 'Mon')                                               as month_name,
    (extract(month from d)::int between 5 and 10)                   as rainy_season_approx
from generate_series(
    '1961-01-01'::date,
    (date_trunc('year', current_date) + interval '11 months')::date,
    interval '1 month'
) as d
