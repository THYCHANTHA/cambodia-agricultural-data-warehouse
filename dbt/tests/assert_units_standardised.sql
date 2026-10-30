-- Unit standardisation: crop production is tonnes, area is hectares, yield is kg/ha after Silver.
select element_name, unit from {{ ref('stg_faostat_production') }}
where (element_name = 'Production' and item_code < 1700 and unit not in ('t', 'animals', 'number'))
   or (element_name = 'Area harvested' and unit <> 'ha')
   or (element_name = 'Yield' and unit not in ('kg/ha', 'g_per_animal', 'kg_per_animal', 'eggs_per_animal'))
