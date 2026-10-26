"""Machine relationships and operational metrics."""

from fastapi import APIRouter, HTTPException

from app import database
from app.schemas import MachineResponse

router = APIRouter()

MACHINES_QUERY = """
WITH production AS (
    SELECT
        machine_id,
        SUM(total_units)::BIGINT AS production_quantity,
        SUM(target_units)::BIGINT AS production_target
    FROM production_records
    GROUP BY machine_id
),
downtime AS (
    SELECT
        pr.machine_id,
        SUM(EXTRACT(EPOCH FROM (de.ended_at - de.started_at)) / 60.0)
            AS unplanned_downtime_minutes
    FROM downtime_events AS de
    JOIN production_records AS pr ON pr.id = de.production_record_id
    WHERE NOT de.is_planned
    GROUP BY pr.machine_id
),
quality AS (
    SELECT
        pr.machine_id,
        SUM(qi.inspected_units)::BIGINT AS inspected_units,
        SUM(qi.defective_units)::BIGINT AS defective_units
    FROM quality_inspections AS qi
    JOIN production_records AS pr ON pr.id = qi.production_record_id
    GROUP BY pr.machine_id
)
SELECT
    m.id AS machine_id,
    m.machine_code,
    m.name AS machine_name,
    m.machine_type,
    m.rated_capacity_per_hour,
    pl.id AS line_id,
    pl.line_code,
    pl.name AS line_name,
    f.id AS factory_id,
    f.name AS factory_name,
    COALESCE(p.production_quantity, 0)::BIGINT AS production_quantity,
    COALESCE(p.production_target, 0)::BIGINT AS production_target,
    ROUND(
        100.0 * p.production_quantity / NULLIF(p.production_target, 0),
        2
    ) AS target_attainment_pct,
    ROUND(COALESCE(d.unplanned_downtime_minutes, 0)::NUMERIC, 2)
        AS unplanned_downtime_minutes,
    COALESCE(q.inspected_units, 0)::BIGINT AS inspected_units,
    COALESCE(q.defective_units, 0)::BIGINT AS defective_units,
    ROUND(
        100.0 * q.defective_units / NULLIF(q.inspected_units, 0),
        2
    ) AS defect_rate_pct
FROM machines AS m
JOIN production_lines AS pl ON pl.id = m.production_line_id
JOIN factories AS f ON f.id = pl.factory_id
LEFT JOIN production AS p ON p.machine_id = m.id
LEFT JOIN downtime AS d ON d.machine_id = m.id
LEFT JOIN quality AS q ON q.machine_id = m.id
ORDER BY f.name, pl.line_code, m.machine_code
"""


@router.get("/machines", response_model=list[MachineResponse])
def machines() -> list[MachineResponse]:
    try:
        rows = database.fetch_all(MACHINES_QUERY)
    except database.DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=503, detail="Database unavailable."
        ) from error
    return [MachineResponse(**row) for row in rows]
