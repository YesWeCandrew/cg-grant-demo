select distinct

    organization_id,
    organization

from {{ref('stg_grants')}}

where organization is not null

order by organization ASC