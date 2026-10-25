with grants as (

    select distinct

        grant_id,
        grant,
        amount,
        focus_area_id,
        grant_date_text,
        grant_date,
        organization_id,
        details

    from {{ref('stg_grants')}}

),

-- New column to provide more data about number of grants to org. 
-- Grants in the same month are ordered by the grant_id hash.
-- Grants with no organization are always a first grant as data is missing to determine otherwise.
sequenced as (

    select

        *,
        row_number() over (
            partition by coalesce(organization_id, grant_id)
            order by grant_date, grant_id
        )                                                   as org_grant_number,
        lag(grant_date) over (
            partition by coalesce(organization_id, grant_id)
            order by grant_date, grant_id
        )                                                   as previous_grant_date

    from grants

)

select

    *,
    date_diff(grant_date, previous_grant_date, month)       as months_since_previous_grant,
    case
        when org_grant_number = 1
        then 'First'
        else 'Repeat'
    end                                                     as grant_sequence

from sequenced
