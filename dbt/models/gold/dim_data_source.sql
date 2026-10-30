-- Grain: one row per source system, with the most recent successful ingestion attached.
with latest as (
    select distinct on (source_name)
        source_name, batch_id, finished_at, source_version, source_sha256
    from {{ source('audit', 'ingestion_log') }}
    where status = 'succeeded'
    order by source_name, finished_at desc
)
select
    s.source_name   as source_key,
    s.publisher, s.description, s.url, s.licence_summary, s.native_grain,
    l.batch_id      as latest_batch_id,
    l.finished_at   as latest_loaded_at,
    l.source_version, l.source_sha256
from {{ ref('data_sources') }} s
left join latest l on l.source_name = s.source_name
