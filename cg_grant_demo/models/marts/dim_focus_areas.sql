select distinct

    focus_area_id,
    focus_area

from {{ref('stg_grants')}}

where focus_area is not null

order by focus_area ASC