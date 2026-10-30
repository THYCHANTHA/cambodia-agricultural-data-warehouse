select trim(flag) as flag, trim(description) as description
from {{ source('bronze', 'faostat_flags') }}
