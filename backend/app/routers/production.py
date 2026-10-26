"""Production trends and production-line metrics."""

from fastapi import APIRouter, HTTPException

from app import database
from app.schemas import ProductionLineResponse, ProductionTrendResponse

router = APIRouter()

TRENDS_QUERY = """
SELECT
    production_date,
    SUM(total_units)::BIGINT AS production_quantity,
    SUM(good_units)::BIGINT AS good_quantity,
    SUM(target_units)::BIGINT AS production_target
FROM production_records
GROUP BY production_date
ORDER BY production_date
"""

LINES_QUERY = """
WITH production AS (
    SELECT
        m.production_line_id,
        SUM(pr.total_units)::BIGINT AS production_quantity,
        SUM(pr.target_units)::BIGINT AS production_target
    FROM production_records AS pr
    JOIN machines AS m ON m.id = pr.machine_id
    GROUP BY m.production_line_id
),
downtime AS (
    SELECT
        m.production_line_id,
        SUM(EXTRACT(EPOCH FROM (de.ended_at - de.started_at)) / 60.0)
            AS unplanned_downtime_minutes
    FROM downtime_events AS de
    JOIN production_records AS pr ON pr.id = de.production_record_id
    JOIN machines AS m ON m.id = pr.machine_id
    WHERE NOT de.is_planned
    GROUP BY m.production_line_id
)
SELECT
    pl.id AS line_id,
    pl.line_code,
    pl.name AS line_name,
    f.name AS factory_name,
    COALESCE(p.production_quantity, 0)::BIGINT AS production_quantity,
    COALESCE(p.production_target, 0)::BIGINT AS production_target,
    ROUND(
        100.0 * p.production_quantity / NULLIF(p.production_target, 0),
        2
    ) AS target_attainment_pct,
    ROUND(COALESCE(d.unplanned_downtime_minutes, 0)::NUMERIC, 2)
        AS unplanned_downtime_minutes
FROM production_lines AS pl
JOIN factories AS f ON f.id = pl.factory_id
LEFT JOIN production AS p ON p.production_line_id = pl.id
LEFT JOIN downtime AS d ON d.production_line_id = pl.id
ORDER BY f.name, pl.line_code
"""


@router.get("/production/trends", response_model=list[ProductionTrendResponse])
def production_trends() -> list[ProductionTrendResponse]:
    try:
        rows = database.fetch_all(TRENDS_QUERY)
    except database.DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=503, detail="Database unavailable."
        ) from error
    return [ProductionTrendResponse(**row) for row in rows]


@router.get("/production/lines", response_model=list[ProductionLineResponse])
def production_lines() -> list[ProductionLineResponse]:
    try:
        rows = database.fetch_all(LINES_QUERY)
    except database.DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=503, detail="Database unavailable."
        ) from error
    return [ProductionLineResponse(**row) for row in rows]
