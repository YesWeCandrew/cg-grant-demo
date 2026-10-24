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