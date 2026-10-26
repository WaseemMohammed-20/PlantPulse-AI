"""Plant-wide overview metrics."""

from fastapi import APIRouter, HTTPException

from app import database
from app.schemas import OverviewResponse

router = APIRouter()

OVERVIEW_QUERY = """
WITH production AS (
    SELECT
        COALESCE(SUM(total_units), 0)::BIGINT AS production_quantity,
        COALESCE(SUM(target_units), 0)::BIGINT AS production_target
    FROM production_records
),
record_downtime AS (
    SELECT
        production_record_id,
        SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0)
            AS downtime_minutes
    FROM downtime_events
    WHERE NOT is_planned
    GROUP BY production_record_id
),
downtime AS (
    SELECT COALESCE(
        SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0),
        0
    ) AS unplanned_downtime_minutes
    FROM downtime_events
    WHERE NOT is_planned
),
oee AS (
    SELECT
        SUM(pr.planned_production_minutes)::NUMERIC AS planned_minutes,
        SUM(GREATEST(
            pr.planned_production_minutes - COALESCE(rd.downtime_minutes, 0),
            0
        )) AS run_minutes,
        SUM(pr.total_units)::NUMERIC AS total_units,
        SUM(pr.good_units)::NUMERIC AS good_units,
        SUM(
            m.rated_capacity_per_hour
            * GREATEST(
                pr.planned_production_minutes - COALESCE(rd.downtime_minutes, 0),
                0
            ) / 60.0
        ) AS theoretical_run_units
    FROM production_records AS pr
    JOIN machines AS m ON m.id = pr.machine_id
    LEFT JOIN record_downtime AS rd ON rd.production_record_id = pr.id
),
quality AS (
    SELECT
        COALESCE(SUM(inspected_units), 0)::BIGINT AS inspected_units,
        COALESCE(SUM(defective_units), 0)::BIGINT AS defective_units
    FROM quality_inspections
)
SELECT
    production_quantity,
    production_target,
    ROUND(
        100.0 * production_quantity / NULLIF(production_target, 0),
        2
    ) AS target_attainment_pct,
    ROUND(
        100.0
            * oee.run_minutes / NULLIF(oee.planned_minutes, 0)
            * oee.total_units / NULLIF(oee.theoretical_run_units, 0)
            * oee.good_units / NULLIF(oee.total_units, 0),
        2
    ) AS oee_pct,
    ROUND(unplanned_downtime_minutes::NUMERIC, 2)
        AS unplanned_downtime_minutes,
    inspected_units,
    defective_units,
    ROUND(
        100.0 * defective_units / NULLIF(inspected_units, 0),
        2
    ) AS defect_rate_pct
FROM production
CROSS JOIN downtime
CROSS JOIN oee
CROSS JOIN quality
"""


@router.get("/overview", response_model=OverviewResponse)
def overview() -> OverviewResponse:
    try:
        rows = database.fetch_all(OVERVIEW_QUERY)
    except database.DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=503, detail="Database unavailable."
        ) from error
    if not rows:
        raise HTTPException(status_code=503, detail="Overview query returned no row.")
    return OverviewResponse(**rows[0])
