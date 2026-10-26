"""Quality metrics grouped by production line."""

from fastapi import APIRouter, HTTPException

from app import database
from app.schemas import QualityLineResponse

router = APIRouter()

QUALITY_LINES_QUERY = """
WITH quality AS (
    SELECT
        pr.machine_id,
        SUM(qi.inspected_units)::BIGINT AS inspected_units,
        SUM(qi.defective_units)::BIGINT AS defective_units
    FROM quality_inspections AS qi
    JOIN production_records AS pr ON pr.id = qi.production_record_id
    GROUP BY pr.machine_id
),
line_quality AS (
    SELECT
        m.production_line_id,
        SUM(q.inspected_units)::BIGINT AS inspected_units,
        SUM(q.defective_units)::BIGINT AS defective_units
    FROM machines AS m
    JOIN quality AS q ON q.machine_id = m.id
    GROUP BY m.production_line_id
)
SELECT
    pl.id AS line_id,
    pl.line_code,
    pl.name AS line_name,
    f.name AS factory_name,
    COALESCE(q.inspected_units, 0)::BIGINT AS inspected_units,
    COALESCE(q.defective_units, 0)::BIGINT AS defective_units,
    ROUND(
        100.0 * q.defective_units / NULLIF(q.inspected_units, 0),
        2
    ) AS defect_rate_pct
FROM production_lines AS pl
JOIN factories AS f ON f.id = pl.factory_id
LEFT JOIN line_quality AS q ON q.production_line_id = pl.id
ORDER BY f.name, pl.line_code
"""


@router.get("/quality/lines", response_model=list[QualityLineResponse])
def quality_lines() -> list[QualityLineResponse]:
    try:
        rows = database.fetch_all(QUALITY_LINES_QUERY)
    except database.DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=503, detail="Database unavailable."
        ) from error
    return [QualityLineResponse(**row) for row in rows]
