-- An organization's first grant should always be its earliest.
-- This checks that no grant is labelled as 'First' if there is another earlier grant.
-- An exception is made for grants without an organization as we do not know who they went to.

with earliest_grant_by_organisation as (

    select
        
        organization_id,
        min(grant_date)     as earliest_grant_date

    from {{ ref('fct_grants') }}

    where organization_id is not null

    group by organization_id

)

select *

from {{ ref('fct_grants') }} grants

join earliest_grant_by_organisation e
  on e.organization_id = grants.organization_id

where grants.grant_sequence = 'First'
    and grants.grant_date > e.earliest_grant_date
    and grants.organization_id is not null
