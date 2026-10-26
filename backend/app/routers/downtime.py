"""Downtime causes and machine rankings."""

from fastapi import APIRouter, HTTPException

from app import database
from app.schemas import DowntimeCauseResponse, DowntimeMachineResponse

router = APIRouter()

CAUSES_QUERY = """
SELECT
    cause,
    is_planned,
    COUNT(*)::BIGINT AS event_count,
    ROUND(
        SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0)::NUMERIC,
        2
    ) AS downtime_minutes
FROM downtime_events
GROUP BY cause, is_planned
ORDER BY downtime_minutes DESC, cause, is_planned
"""

MACHINES_QUERY = """
WITH downtime AS (
    SELECT
        pr.machine_id,
        COUNT(*)::BIGINT AS unplanned_event_count,
        SUM(EXTRACT(EPOCH FROM (de.ended_at - de.started_at)))
            AS downtime_seconds
    FROM downtime_events AS de
    JOIN production_records AS pr ON pr.id = de.production_record_id
    WHERE NOT de.is_planned
    GROUP BY pr.machine_id
)
SELECT
    RANK() OVER (ORDER BY d.downtime_seconds DESC)::BIGINT AS downtime_rank,
    m.id AS machine_id,
    m.machine_code,
    m.name AS machine_name,
    pl.name AS production_line,
    f.name AS factory_name,
    d.unplanned_event_count,
    ROUND((d.downtime_seconds / 60.0)::NUMERIC, 2)
        AS unplanned_downtime_minutes
FROM downtime AS d
JOIN machines AS m ON m.id = d.machine_id
JOIN production_lines AS pl ON pl.id = m.production_line_id
JOIN factories AS f ON f.id = pl.factory_id
ORDER BY d.downtime_seconds DESC, m.machine_code
"""


@router.get("/downtime/causes", response_model=list[DowntimeCauseResponse])
def downtime_causes() -> list[DowntimeCauseResponse]:
    try:
        rows = database.fetch_all(CAUSES_QUERY)
    except database.DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=503, detail="Database unavailable."
        ) from error
    return [DowntimeCauseResponse(**row) for row in rows]


@router.get("/downtime/machines", response_model=list[DowntimeMachineResponse])
def downtime_machines() -> list[DowntimeMachineResponse]:
    try:
        rows = database.fetch_all(MACHINES_QUERY)
    except database.DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=503, detail="Database unavailable."
        ) from error
    return [DowntimeMachineResponse(**row) for row in rows]
