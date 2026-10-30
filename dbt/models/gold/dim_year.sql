{{ config(post_hook="alter table {{ this }} add primary key (year)") }}
-- Grain: one row per calendar year (from 1960, the first World Bank observation year). Annual facts
-- (FAOSTAT, World Bank) reference this dimension.
select
    y::int                  as year,
    (y::int / 10) * 10      as decade
from generate_series(1960, extract(year from current_date)::int) as y
