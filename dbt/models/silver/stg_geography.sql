-- Silver: Cambodian provinces (ADM1) from geoBoundaries. Names are trimmed; ids are the stable key.
select
    shape_id                     as province_id,
    trim(shape_name)             as province_name,
    nullif(shape_iso, '')        as province_iso,
    shape_group                  as country_iso3,
    geometry_geojson,
    _batch_id,
    _loaded_at
from {{ source('bronze', 'geoboundaries_adm1') }}
