-- Grain: one row per geographic unit. Hierarchy: country -> province.
-- Surrogate keys are deterministic hashes of the level and natural id, so reloads never reshuffle keys.
-- No slowly-changing history: the sources provide a single boundary vintage (geoBoundaries 2017),
-- so Type-2 versioning would record nothing real. Revisit if dated boundary releases are added.
with country as (
    select
        'country'::text  as geography_level,
        'KHM'::text      as natural_id,
        'Cambodia'::text as geography_name,
        null::text       as parent_natural_id,
        'KHM'::text      as country_iso3,
        null::text       as province_iso
),
provinces as (
    select
        'province'::text, province_id, province_name, 'KHM'::text, country_iso3, province_iso
    from {{ ref('stg_geography') }}
)
select
    md5(geography_level || '|' || natural_id)                       as geography_key,
    case when parent_natural_id is null then null
         else md5('country|' || parent_natural_id) end              as parent_geography_key,
    geography_level, natural_id, geography_name, country_iso3, province_iso
from (select * from country union all select * from provinces) u
