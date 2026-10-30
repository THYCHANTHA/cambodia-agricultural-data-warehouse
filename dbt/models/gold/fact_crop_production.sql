-- Grain: one row per country x year x crop item. FAOSTAT is national only: provincial yield is
-- NOT available here and must never be inferred from this table.
-- Production (t), area harvested (ha) and reported yield come from the same FAOSTAT record set, so
-- they share one fact. yield_derived_kg_ha = production_t * 1000 / area_ha is a cross-check.
with pivoted as (
    select
        item_code,
        year,
        max(value) filter (where element_name = 'Production')     as production_t,
        max(value) filter (where element_name = 'Area harvested') as area_harvested_ha,
        max(value) filter (where element_name = 'Yield')          as yield_reported_kg_ha,
        max(flag)  filter (where element_name = 'Production')     as production_flag,
        max(flag)  filter (where element_name = 'Area harvested') as area_flag,
        max(flag)  filter (where element_name = 'Yield')          as yield_flag
    from {{ ref('stg_faostat_production') }}
    where element_name in ('Production', 'Area harvested', 'Yield')
    group by item_code, year
)
select
    md5('country|KHM')                  as geography_key,
    p.item_code                         as crop_key,
    p.year,
    'faostat_production'                as source_key,
    p.production_t,
    p.area_harvested_ha,
    p.yield_reported_kg_ha,
    case when p.area_harvested_ha > 0
         then p.production_t * 1000 / p.area_harvested_ha end   as yield_derived_kg_ha,
    case when p.area_harvested_ha > 0 and p.yield_reported_kg_ha > 0
         then abs(p.production_t * 1000 / p.area_harvested_ha - p.yield_reported_kg_ha)
              / p.yield_reported_kg_ha * 100 end                as yield_discrepancy_pct,
    p.production_flag,
    p.area_flag,
    p.yield_flag
from pivoted p
join {{ ref('dim_crop') }} c
  on c.crop_key = p.item_code and c.item_type = 'crop'
