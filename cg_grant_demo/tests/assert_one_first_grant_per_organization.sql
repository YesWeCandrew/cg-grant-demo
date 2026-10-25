-- Every organization should have exactly one first grant.
-- Returns organizations with none or more than one.

select

    organization_id,
    countif(grant_sequence = 'First')   as first_grants

from {{ ref('fct_grants') }}

where organization_id is not null

group by organization_id

having first_grants != 1
