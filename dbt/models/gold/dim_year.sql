-- Grain: one row per calendar year. Annual facts (FAOSTAT, World Bank) reference this dimension.
select
    y::int                  as year,
    (y::int / 10) * 10      as decade
from generate_series(1961, extract(year from current_date)::int) as y
