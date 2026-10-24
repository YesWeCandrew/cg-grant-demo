select

    renewed.grant_id                                        as renewed_grant_id,
    first.grant_id                                          as first_grant_id,
    org.organization                                        as organization,
    renewed.grant                                           as renewed_grant,
    first.grant                                             as first_grant,
    renewed.grant_date                                      as renewed_grant_date,
    first.grant_date                                        as first_grant_date,
    date_diff(renewed.grant_date, first.grant_date, month)  as months_since_first,
    safe_divide(renewed.amount, first.amount)               as amount_ratio,
    renewed.amount                                          as renewed_amount,
    first.amount                                            as first_amount,
    renewed_fa.focus_area                                   as renewed_focus_area,
    first_fa.focus_area                                     as first_focus_area,
    renewed.focus_area_id = first.focus_area_id             as same_focus_area,
    renewed.details                                         as renewed_details,
    first.details                                           as first_details

from {{ ref('fct_grants') }} renewed

join {{ ref('fct_grants') }} first
    on renewed.organization_id = first.organization_id
    and first.grant_date <= renewed.grant_date
    and first.grant_id != renewed.grant_id

join {{ ref('dim_organizations')}} org
    on org.organization_id = first.organization_id

join {{ ref('dim_focus_areas')}} first_fa
    on first_fa.focus_area_id = first.focus_area_id

join {{ ref('dim_focus_areas')}} renewed_fa
    on renewed_fa.focus_area_id = renewed.focus_area_id

where date_diff(renewed.grant_date, first.grant_date, month) <= 60