-- All the repeat grants should appear in the pairs data mart, and vice versa.
-- Returns grants where fct_grants and mart_grant_pairs disagree.

with paired as (

    select distinct renewed_grant_id as grant_id

    from {{ ref('mart_grant_pairs') }}

)

select

    grants.grant_id,
    grants.grant_sequence,
    paired.grant_id is not null         as in_grant_pairs

from {{ ref('fct_grants') }} grants

left join paired
    on paired.grant_id = grants.grant_id

where (grants.grant_sequence = 'Repeat') != (paired.grant_id is not null)
