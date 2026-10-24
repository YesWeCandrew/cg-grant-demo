with source as (
    select * from {{source ('raw', 'cg_grants_archive')}}
),

cleaned as (
    select
        trim(Grant)                             as grant,
        trim(`Organization Name`)               as organization,
        trim(`Focus Area`)                      as focus_area,
        Amount                                  as amount,
        Date                                    as grant_date_text,
        safe.parse_date('%B %Y', trim(Date))    as grant_date,
        trim(Details)                           as details

    from source
),

-- There is a duplicate in the data, but I would want future duplicates
-- to come through and fail data quality rules so we can work out if they
-- are real duplicates or not, rather than be removed silently, so tiebraker
-- only removes the known duplicate

numbered as (
    
    select

        *,
        {{ dbt_utils.generate_surrogate_key([
            'grant',
            'organization',
            'grant_date_text',
            'amount'
            ]) }}                                                   as grant_id,
        {{dbt_utils.generate_surrogate_key(['organization'])}}        as organization_id,
        {{dbt_utils.generate_surrogate_key(['focus_area'])}}          as focus_area_id,
        row_number() over (
            partition by grant, organization, grant_date_text, amount
            order by grant
        ) as dup_num
    
    from cleaned

)

-- generating unique ids for each row
select
  
    grant_id,
    grant,
    amount,
    focus_area,
    case 
        when focus_area is null
        then focus_area_id 
        else null
    end                   as focus_area_id,
    grant_date_text,
    grant_date,
    organization,
    case 
        when organization is null
        then organization_id 
        else null
    end                   as organization_id,
    details

from numbered

-- This ensures future potential duplicates would come through and fail data quality rules
-- rather than failing silently.
WHERE 
    (grant_id <> 'cb95d2c1b262ed80b0a744f1c21f3e0f') -- RAND duplicate row
    OR dup_num = 1