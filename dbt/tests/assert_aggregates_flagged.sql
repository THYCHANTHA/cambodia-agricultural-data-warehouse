-- FAOSTAT aggregate items (code >= 1700) must always be flagged so they are never summed with members.
select crop_key, item_name from {{ ref('dim_crop') }} where crop_key >= 1700 and not is_aggregate
