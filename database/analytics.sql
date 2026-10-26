-- OEE by factory, production line, and machine.
-- Assumptions:
--   * Each production record represents one machine shift.
--   * planned_production_minutes excludes scheduled breaks.
--   * Availability deducts unplanned downtime only; planned events are excluded.
--   * Performance compares actual units with rated capacity during run time.
--   * Quality uses good_units / total_units from the production record.
--   * OEE is availability * performance * quality; ratios are time-weighted
--     by summing their numerators and denominators before division.
WITH downtime_by_record AS (
    SELECT
        production_record_id,
        SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0) AS downtime_minutes
    FROM downtime_events
    WHERE NOT is_planned
    GROUP BY production_record_id
),
shift_metrics AS (
    SELECT
        f.name AS factory,
        pl.name AS production_line,
        m.machine_code,
        m.name AS machine,
        pr.planned_production_minutes::NUMERIC AS planned_minutes,
        GREATEST(
            pr.planned_production_minutes
                - COALESCE(d.downtime_minutes, 0),
            0
        ) AS run_minutes,
        pr.total_units::NUMERIC AS total_units,
        pr.good_units::NUMERIC AS good_units,
        m.rated_capacity_per_hour
            * GREATEST(
                pr.planned_production_minutes
                    - COALESCE(d.downtime_minutes, 0),
                0
            ) / 60.0 AS theoretical_run_units
    FROM production_records AS pr
    JOIN machines AS m ON m.id = pr.machine_id
    JOIN production_lines AS pl ON pl.id = m.production_line_id
    JOIN factories AS f ON f.id = pl.factory_id
    LEFT JOIN downtime_by_record AS d
        ON d.production_record_id = pr.id
)
SELECT
    factory,
    production_line,
    machine_code,
    machine,
    ROUND(
        100.0 * SUM(run_minutes) / NULLIF(SUM(planned_minutes), 0),
        2
    ) AS availability_pct,
    ROUND(
        100.0 * SUM(total_units)
            / NULLIF(SUM(theoretical_run_units), 0),
        2
    ) AS performance_pct,
    ROUND(
        100.0 * SUM(good_units) / NULLIF(SUM(total_units), 0),
        2
    ) AS quality_pct,
    ROUND(
        100.0
            * SUM(run_minutes) / NULLIF(SUM(planned_minutes), 0)
            * SUM(total_units) / NULLIF(SUM(theoretical_run_units), 0)
            * SUM(good_units) / NULLIF(SUM(total_units), 0),
        2
    ) AS oee_pct
FROM shift_metrics
GROUP BY factory, production_line, machine_code, machine
ORDER BY factory, production_line, machine_code;

-- Production target attainment by factory, line, and production date.
SELECT
    f.name AS factory,
    pl.name AS production_line,
    pr.production_date,
    SUM(pr.total_units) AS actual_units,
    SUM(pr.target_units) AS target_units,
    ROUND(
        100.0 * SUM(pr.total_units) / NULLIF(SUM(pr.target_units), 0),
        2
    ) AS target_attainment_pct
FROM production_records AS pr
JOIN machines AS m ON m.id = pr.machine_id
JOIN production_lines AS pl ON pl.id = m.production_line_id
JOIN factories AS f ON f.id = pl.factory_id
GROUP BY f.name, pl.name, pr.production_date
ORDER BY pr.production_date, factory, production_line;

-- Machine downtime by cause, separating planned from unplanned events.
SELECT
    f.name AS factory,
    pl.name AS production_line,
    m.machine_code,
    m.name AS machine,
    de.cause,
    de.is_planned,
    COUNT(*) AS event_count,
    ROUND(
        SUM(EXTRACT(EPOCH FROM (de.ended_at - de.started_at)) / 60.0),
        2
    ) AS downtime_minutes
FROM downtime_events AS de
JOIN production_records AS pr ON pr.id = de.production_record_id
JOIN machines AS m ON m.id = pr.machine_id
JOIN production_lines AS pl ON pl.id = m.production_line_id
JOIN factories AS f ON f.id = pl.factory_id
GROUP BY f.name, pl.name, m.machine_code, m.name, de.cause, de.is_planned
ORDER BY downtime_minutes DESC;

-- Defect rate by production line, based on inspected sample units.
SELECT
    f.name AS factory,
    pl.name AS production_line,
    SUM(qi.inspected_units) AS inspected_units,
    SUM(qi.defective_units) AS defective_units,
    ROUND(
        100.0 * SUM(qi.defective_units)
            / NULLIF(SUM(qi.inspected_units), 0),
        2
    ) AS defect_rate_pct
FROM quality_inspections AS qi
JOIN production_records AS pr ON pr.id = qi.production_record_id
JOIN machines AS m ON m.id = pr.machine_id
JOIN production_lines AS pl ON pl.id = m.production_line_id
JOIN factories AS f ON f.id = pl.factory_id
GROUP BY f.name, pl.name
ORDER BY defect_rate_pct DESC;

-- Daily production trend by factory and production line.
SELECT
    pr.production_date,
    f.name AS factory,
    pl.name AS production_line,
    SUM(pr.total_units) AS total_units,
    SUM(pr.good_units) AS good_units,
    SUM(pr.target_units) AS target_units
FROM production_records AS pr
JOIN machines AS m ON m.id = pr.machine_id
JOIN production_lines AS pl ON pl.id = m.production_line_id
JOIN factories AS f ON f.id = pl.factory_id
GROUP BY pr.production_date, f.name, pl.name
ORDER BY pr.production_date, factory, production_line;

-- Machine downtime ranking by accumulated unplanned downtime minutes.
SELECT
    RANK() OVER (
        ORDER BY SUM(EXTRACT(EPOCH FROM (de.ended_at - de.started_at))) DESC
    ) AS downtime_rank,
    f.name AS factory,
    pl.name AS production_line,
    m.machine_code,
    m.name AS machine,
    COUNT(*) AS unplanned_event_count,
    ROUND(
        SUM(EXTRACT(EPOCH FROM (de.ended_at - de.started_at)) / 60.0),
        2
    ) AS unplanned_downtime_minutes
FROM downtime_events AS de
JOIN production_records AS pr ON pr.id = de.production_record_id
JOIN machines AS m ON m.id = pr.machine_id
JOIN production_lines AS pl ON pl.id = m.production_line_id
JOIN factories AS f ON f.id = pl.factory_id
WHERE NOT de.is_planned
GROUP BY f.name, pl.name, m.machine_code, m.name
ORDER BY unplanned_downtime_minutes DESC, m.machine_code;
