-- One row per day, which the Semantic Layer uses to group metrics by time.
-- Covers the full range of grant dates.

with days as (

    {{ dbt.date_spine(
        'day',
        "date '2012-01-01'",
        "date '2027-01-01'"
    ) }}

)

select cast(date_day as date) as date_day

from days
