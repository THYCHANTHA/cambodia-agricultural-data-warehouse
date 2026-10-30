-- Silver: typed, de-duplicated, unit-standardised FAOSTAT observations (all items and elements).
-- Blank source values are kept as NULL (never imputed); FAOSTAT flag 'M' marks them as missing.
with typed as (
    select
        area_code_m49,
        item_code::int                          as item_code,
        item_code_cpc,
        trim(item)                              as item_name,
        element_code::int                       as element_code,
        trim(element)                           as element_name,
        year::int                               as year,
        trim(unit)                              as source_unit,
        nullif(trim(value), '')::numeric        as source_value,
        nullif(trim(flag), '')                  as flag,
        _batch_id,
        _loaded_at
    from {{ source('bronze', 'faostat_production') }}
),
deduped as (
    select *, row_number() over (
        partition by item_code, element_code, year
        order by _loaded_at desc
    ) as rn
    from typed
)
select
    d.item_code, d.item_code_cpc, d.item_name,
    d.element_code, d.element_name, d.year,
    m.canonical_unit                            as unit,
    d.source_value * m.factor                   as value,
    d.source_unit,
    d.flag,
    (d.source_value is null)                    as is_missing,
    d._batch_id, d._loaded_at
from deduped d
left join {{ ref('faostat_unit_map') }} m on m.source_unit = d.source_unit
where d.rn = 1
