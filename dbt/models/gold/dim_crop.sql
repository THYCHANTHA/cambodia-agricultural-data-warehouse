{{ config(post_hook="alter table {{ this }} add primary key (crop_key)") }}
-- Grain: one row per FAOSTAT item. item_type is derived from which elements the item reports:
--   crop               reports 'Area harvested'
--   livestock          reports animal-count elements (stocks, producing/slaughtered, laying, milk animals)
--   processed_product  everything else (oils, sugar, beer ... report 'Production' only)
-- is_aggregate marks FAOSTAT group items (codes >= 1700, e.g. Cereals, primary). Never sum an
-- aggregate together with its member items.
with per_item as (
    select
        item_code,
        max(item_name)      as item_name,
        max(item_code_cpc)  as cpc_code,
        bool_or(element_name = 'Area harvested') as has_area,
        bool_or(element_name in ('Stocks', 'Producing Animals/Slaughtered', 'Milk Animals', 'Laying')) as has_animals
    from {{ ref('stg_faostat_production') }}
    group by item_code
)
select
    item_code                                   as crop_key,
    item_name,
    cpc_code,
    case when has_area then 'crop'
         when has_animals then 'livestock'
         else 'processed_product' end           as item_type,
    (item_code >= 1700)                         as is_aggregate
from per_item
