"""Provision PlantPulse SQL datasets, charts, and dashboards in Superset."""

from __future__ import annotations

import json
import secrets
import uuid
from typing import Any

from sqlalchemy import text

SIMULATED = "SIMULATED SOURCE DATA - not live factory measurements."

DATASETS: dict[str, dict[str, Any]] = {
    "pp_production_daily": {
        "description": f"{SIMULATED} One row per date, factory, and line.",
        "main_dttm_col": "production_date",
        "sql": """
SELECT
    pr.production_date,
    f.name AS factory,
    f.name || ' / ' || pl.name AS production_line,
    pl.line_code,
    pl.name AS line_name,
    SUM(pr.total_units)::BIGINT AS total_units,
    SUM(pr.good_units)::BIGINT AS good_units,
    SUM(pr.target_units)::BIGINT AS target_units
FROM public.production_records AS pr
JOIN public.machines AS m ON m.id = pr.machine_id
JOIN public.production_lines AS pl ON pl.id = m.production_line_id
JOIN public.factories AS f ON f.id = pl.factory_id
GROUP BY pr.production_date, f.name, pl.name, pl.line_code
""",
        "metrics": {
            "total_units": ("SUM(total_units)", "Actual units", ",.0f"),
            "good_units": ("SUM(good_units)", "Good units", ",.0f"),
            "target_units": ("SUM(target_units)", "Target units", ",.0f"),
            "target_attainment_pct": (
                "100.0 * SUM(total_units) / NULLIF(SUM(target_units), 0)",
                "Target attainment (%)",
                ".2f",
            ),
        },
    },
    "pp_downtime": {
        "description": (
            f"{SIMULATED} One row per date, factory, line, machine, cause, "
            "and planned/unplanned classification. Duration is summed event "
            "time; overlapping events are not deduplicated."
        ),
        "main_dttm_col": "downtime_date",
        "sql": """
SELECT
    de.started_at::DATE AS downtime_date,
    f.name AS factory,
    f.name || ' / ' || pl.name AS production_line,
    pl.line_code,
    pl.name AS line_name,
    m.machine_code,
    m.machine_code || ' / ' || m.name AS machine,
    m.name AS machine_name,
    de.cause,
    de.is_planned,
    COUNT(*)::BIGINT AS event_count,
    SUM(EXTRACT(EPOCH FROM (de.ended_at - de.started_at)) / 60.0)
        AS downtime_minutes,
    SUM(
        CASE WHEN NOT de.is_planned
            THEN EXTRACT(EPOCH FROM (de.ended_at - de.started_at)) / 60.0
            ELSE 0
        END
    ) AS unplanned_downtime_minutes
FROM public.downtime_events AS de
JOIN public.production_records AS pr ON pr.id = de.production_record_id
JOIN public.machines AS m ON m.id = pr.machine_id
JOIN public.production_lines AS pl ON pl.id = m.production_line_id
JOIN public.factories AS f ON f.id = pl.factory_id
GROUP BY
    de.started_at::DATE, f.name, pl.name, pl.line_code,
    m.machine_code, m.name,
    de.cause, de.is_planned
""",
        "metrics": {
            "event_count": ("SUM(event_count)", "Downtime events", ",.0f"),
            "downtime_minutes": (
                "SUM(downtime_minutes)",
                "Downtime minutes (all)",
                ",.1f",
            ),
            "unplanned_downtime_minutes": (
                "SUM(unplanned_downtime_minutes)",
                "Unplanned downtime (minutes)",
                ",.1f",
            ),
        },
    },
    "pp_quality": {
        "description": (
            f"{SIMULATED} One row per inspection date, factory, and line. "
            "Defect rate denominator is inspected sample units."
        ),
        "main_dttm_col": "inspection_date",
        "sql": """
SELECT
    qi.inspected_at::DATE AS inspection_date,
    f.name AS factory,
    f.name || ' / ' || pl.name AS production_line,
    pl.line_code,
    pl.name AS line_name,
    SUM(qi.inspected_units)::BIGINT AS inspected_units,
    SUM(qi.defective_units)::BIGINT AS defective_units
FROM public.quality_inspections AS qi
JOIN public.production_records AS pr ON pr.id = qi.production_record_id
JOIN public.machines AS m ON m.id = pr.machine_id
JOIN public.production_lines AS pl ON pl.id = m.production_line_id
JOIN public.factories AS f ON f.id = pl.factory_id
GROUP BY qi.inspected_at::DATE, f.name, pl.name, pl.line_code
""",
        "metrics": {
            "inspected_units": (
                "SUM(inspected_units)",
                "Inspected sample units",
                ",.0f",
            ),
            "defective_units": (
                "SUM(defective_units)",
                "Defective sample units",
                ",.0f",
            ),
            "defect_rate_pct": (
                "100.0 * SUM(defective_units) / NULLIF(SUM(inspected_units), 0)",
                "Defect rate of inspected sample (%)",
                ".2f",
            ),
        },
    },
    "pp_machine_performance": {
        "description": (
            f"{SIMULATED} One row per machine and production date. OEE "
            "assumptions: scheduled breaks are excluded from planned time; "
            "availability deducts unplanned downtime only and clamps run time "
            "at zero; performance compares total units to rated capacity "
            "during run time; quality is good units / total units; OEE is the "
            "product of those aggregated ratios."
        ),
        "main_dttm_col": "production_date",
        "sql": """
WITH downtime_by_record AS (
    SELECT
        production_record_id,
        SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0)
            AS unplanned_downtime_minutes
    FROM public.downtime_events
    WHERE NOT is_planned
    GROUP BY production_record_id
),
machine_shifts AS (
    SELECT
        pr.id AS production_record_id,
        pr.production_date,
        f.name AS factory,
        f.name || ' / ' || pl.name AS production_line,
        pl.line_code,
        m.machine_code,
        m.machine_code || ' / ' || m.name AS machine,
        m.name AS machine_name,
        pr.planned_production_minutes::NUMERIC AS planned_minutes,
        GREATEST(
            pr.planned_production_minutes
                - COALESCE(d.unplanned_downtime_minutes, 0),
            0
        ) AS run_minutes,
        COALESCE(d.unplanned_downtime_minutes, 0)
            AS unplanned_downtime_minutes,
        pr.target_units::NUMERIC AS target_units,
        pr.total_units::NUMERIC AS total_units,
        pr.good_units::NUMERIC AS good_units,
        m.rated_capacity_per_hour
            * GREATEST(
                pr.planned_production_minutes
                    - COALESCE(d.unplanned_downtime_minutes, 0),
                0
            ) / 60.0 AS theoretical_run_units
    FROM public.production_records AS pr
    JOIN public.machines AS m ON m.id = pr.machine_id
    JOIN public.production_lines AS pl ON pl.id = m.production_line_id
    JOIN public.factories AS f ON f.id = pl.factory_id
    LEFT JOIN downtime_by_record AS d ON d.production_record_id = pr.id
)
SELECT
    production_date,
    factory,
    production_line,
    line_code,
    machine_code,
    machine,
    SUM(planned_minutes) AS planned_minutes,
    SUM(run_minutes) AS run_minutes,
    SUM(unplanned_downtime_minutes) AS unplanned_downtime_minutes,
    SUM(target_units)::BIGINT AS target_units,
    SUM(total_units)::BIGINT AS total_units,
    SUM(good_units)::BIGINT AS good_units,
    SUM(theoretical_run_units) AS theoretical_run_units
FROM machine_shifts
GROUP BY
    production_date, factory, production_line, line_code,
    machine_code, machine, machine_name
""",
        "metrics": {
            "total_units": ("SUM(total_units)", "Actual units", ",.0f"),
            "good_units": ("SUM(good_units)", "Good units", ",.0f"),
            "target_units": ("SUM(target_units)", "Target units", ",.0f"),
            "unplanned_downtime_minutes": (
                "SUM(unplanned_downtime_minutes)",
                "Unplanned downtime (minutes)",
                ",.1f",
            ),
            "availability_pct": (
                "100.0 * SUM(run_minutes) / NULLIF(SUM(planned_minutes), 0)",
                "Availability (%)",
                ".2f",
            ),
            "performance_pct": (
                "100.0 * SUM(total_units) "
                "/ NULLIF(SUM(theoretical_run_units), 0)",
                "Performance (%)",
                ".2f",
            ),
            "quality_pct": (
                "100.0 * SUM(good_units) / NULLIF(SUM(total_units), 0)",
                "OEE quality factor (%)",
                ".2f",
            ),
            "oee_pct": (
                "100.0 * SUM(run_minutes) / NULLIF(SUM(planned_minutes), 0) "
                "* SUM(total_units) / NULLIF(SUM(theoretical_run_units), 0) "
                "* SUM(good_units) / NULLIF(SUM(total_units), 0)",
                "OEE (%) — simulated estimate",
                ".2f",
            ),
        },
    },
}

CHARTS: list[dict[str, Any]] = [
    {
        "name": "Overview — Production Output vs Target",
        "dataset": "pp_production_daily",
        "viz_type": "echarts_timeseries_line",
        "metrics": ["total_units", "target_units"],
        "groupby": ["production_line"],
        "time": True,
        "description": f"{SIMULATED} Daily actual output and target by line.",
    },
    {
        "name": "Overview — Target Attainment by Line",
        "dataset": "pp_production_daily",
        "viz_type": "table",
        "metrics": ["target_attainment_pct"],
        "groupby": ["production_line"],
        "order_desc": True,
        "description": f"{SIMULATED} Weighted units / target units by line.",
    },
    {
        "name": "Overview — OEE by Production Line",
        "dataset": "pp_machine_performance",
        "viz_type": "table",
        "metrics": ["oee_pct"],
        "groupby": ["production_line"],
        "order_desc": True,
        "description": f"{SIMULATED} OEE estimate using documented assumptions.",
    },
    {
        "name": "Overview — Unplanned Downtime by Cause",
        "dataset": "pp_downtime",
        "viz_type": "table",
        "metrics": ["unplanned_downtime_minutes"],
        "groupby": ["cause"],
        "order_desc": True,
        "description": f"{SIMULATED} Excludes planned downtime.",
    },
    {
        "name": "Overview — Defect Rate by Line",
        "dataset": "pp_quality",
        "viz_type": "table",
        "metrics": ["defect_rate_pct"],
        "groupby": ["production_line"],
        "order_desc": True,
        "description": (
            f"{SIMULATED} Defective inspected sample units / inspected sample "
            "units; not the OEE quality factor."
        ),
    },
    {
        "name": "Production — Daily Output and Target",
        "dataset": "pp_production_daily",
        "viz_type": "echarts_timeseries_line",
        "metrics": ["total_units", "target_units", "good_units"],
        "groupby": ["production_line"],
        "time": True,
        "description": f"{SIMULATED} Daily totals by line.",
    },
    {
        "name": "Production — Actual Units by Line",
        "dataset": "pp_production_daily",
        "viz_type": "table",
        "metrics": ["total_units"],
        "groupby": ["production_line"],
        "order_desc": True,
        "description": f"{SIMULATED} Total units, sorted highest first.",
    },
    {
        "name": "Production — Target Attainment by Day",
        "dataset": "pp_production_daily",
        "viz_type": "echarts_timeseries_line",
        "metrics": ["target_attainment_pct"],
        "groupby": ["production_line"],
        "time": True,
        "description": f"{SIMULATED} Weighted actual units / target units.",
    },
    {
        "name": "Downtime — Unplanned Minutes by Cause",
        "dataset": "pp_downtime",
        "viz_type": "table",
        "metrics": ["unplanned_downtime_minutes"],
        "groupby": ["cause"],
        "order_desc": True,
        "description": f"{SIMULATED} Planned events are excluded.",
    },
    {
        "name": "Downtime — Unplanned Minutes by Machine",
        "dataset": "pp_downtime",
        "viz_type": "table",
        "metrics": ["unplanned_downtime_minutes"],
        "groupby": ["machine"],
        "order_desc": True,
        "description": f"{SIMULATED} Ranked highest downtime first.",
    },
    {
        "name": "Downtime — Cause and Machine Event Detail",
        "dataset": "pp_downtime",
        "viz_type": "table",
        "all_columns": [
            "production_line",
            "line_code",
            "machine_code",
            "machine",
            "cause",
            "is_planned",
            "event_count",
            "downtime_minutes",
        ],
        "order_by_cols": ["downtime_minutes"],
        "order_desc": True,
        "description": f"{SIMULATED} Event duration detail, longest first.",
    },
    {
        "name": "Quality — Defect Rate by Production Line",
        "dataset": "pp_quality",
        "viz_type": "table",
        "metrics": ["defect_rate_pct"],
        "groupby": ["production_line"],
        "order_desc": True,
        "description": (
            f"{SIMULATED} Defect rate denominator is inspected sample units."
        ),
    },
    {
        "name": "Quality — Inspected and Defective Sample Units",
        "dataset": "pp_quality",
        "viz_type": "table",
        "metrics": ["inspected_units", "defective_units"],
        "groupby": ["production_line"],
        "description": (
            f"{SIMULATED} Counts are inspected sample units, not all "
            "production units."
        ),
    },
    {
        "name": "Quality — Daily Defect Rate",
        "dataset": "pp_quality",
        "viz_type": "echarts_timeseries_line",
        "metrics": ["defect_rate_pct"],
        "groupby": ["production_line"],
        "time": True,
        "description": (
            f"{SIMULATED} Weighted defective / inspected sample units by date."
        ),
    },
    {
        "name": "Machine Performance — OEE by Machine",
        "dataset": "pp_machine_performance",
        "viz_type": "table",
        "metrics": ["oee_pct"],
        "groupby": ["machine"],
        "order_desc": True,
        "description": f"{SIMULATED} Ranked OEE estimate by machine.",
    },
    {
        "name": "Machine Performance — Output by Machine",
        "dataset": "pp_machine_performance",
        "viz_type": "table",
        "metrics": ["total_units", "target_units"],
        "groupby": ["machine"],
        "order_desc": True,
        "description": f"{SIMULATED} Actual and target units by machine.",
    },
    {
        "name": "Machine Performance — Unplanned Downtime Ranking",
        "dataset": "pp_machine_performance",
        "viz_type": "table",
        "metrics": ["unplanned_downtime_minutes"],
        "groupby": ["machine"],
        "order_desc": True,
        "description": f"{SIMULATED} Unplanned downtime, highest first.",
    },
]

DASHBOARDS: dict[str, list[str]] = {
    "Manufacturing Overview": [
        "Overview — Production Output vs Target",
        "Overview — Target Attainment by Line",
        "Overview — OEE by Production Line",
        "Overview — Unplanned Downtime by Cause",
        "Overview — Defect Rate by Line",
    ],
    "Production Analytics": [
        "Production — Daily Output and Target",
        "Production — Actual Units by Line",
        "Production — Target Attainment by Day",
    ],
    "Downtime Intelligence": [
        "Downtime — Unplanned Minutes by Cause",
        "Downtime — Unplanned Minutes by Machine",
        "Downtime — Cause and Machine Event Detail",
    ],
    "Quality Analytics": [
        "Quality — Defect Rate by Production Line",
        "Quality — Inspected and Defective Sample Units",
        "Quality — Daily Defect Rate",
    ],
    "Machine Performance": [
        "Machine Performance — OEE by Machine",
        "Machine Performance — Output by Machine",
        "Machine Performance — Unplanned Downtime Ranking",
    ],
}


def _upsert_dataset(database: Database, name: str, spec: dict[str, Any]) -> SqlaTable:
    dataset = (
        db.session.query(SqlaTable)
        .filter_by(database_id=database.id, schema="public", table_name=name)
        .one_or_none()
    )
    if dataset is None:
        dataset = SqlaTable(
            database_id=database.id,
            schema="public",
            table_name=name,
        )
    dataset.sql = spec["sql"].strip()
    dataset.description = spec["description"]
    dataset.main_dttm_col = spec["main_dttm_col"]
    db.session.add(dataset)
    db.session.flush()

    metadata = dataset.external_metadata()
    if not metadata:
        raise RuntimeError(f"No columns were found for dataset {name}.")
    existing_columns = {column.column_name: column for column in dataset.columns}
    for column in metadata:
        column_name = column["column_name"]
        dataset_column = existing_columns.pop(column_name, None)
        if dataset_column is None:
            dataset_column = TableColumn(
                column_name=column_name,
                table=dataset,
            )
        dataset_column.type = column["type"]
        dataset_column.is_dttm = column_name == spec["main_dttm_col"]
        dataset_column.groupby = True
        dataset_column.filterable = True
        if column.get("comment"):
            dataset_column.description = column["comment"]
        db.session.add(dataset_column)
    for obsolete_column in existing_columns.values():
        db.session.delete(obsolete_column)

    existing_metrics = {
        metric.metric_name: metric for metric in dataset.metrics
    }
    expected_metrics = spec["metrics"]
    for metric_name, (expression, verbose_name, d3format) in expected_metrics.items():
        metric = existing_metrics.pop(metric_name, None)
        if metric is None:
            metric = SqlMetric(metric_name=metric_name, table=dataset)
        metric.expression = expression
        metric.verbose_name = verbose_name
        metric.metric_type = "numeric"
        metric.d3format = d3format
        metric.description = spec["description"]
        db.session.add(metric)
    for obsolete_metric in existing_metrics.values():
        db.session.delete(obsolete_metric)
    return dataset


def _chart_form_data(chart: dict[str, Any], dataset: SqlaTable) -> dict[str, Any]:
    form_data: dict[str, Any] = {
        "datasource": f"{dataset.id}__table",
        "viz_type": chart["viz_type"],
        "metrics": chart.get("metrics", []),
        "groupby": chart.get("groupby", []),
        "row_limit": 1000,
        "time_range": "No filter",
        "show_legend": True,
        "color_scheme": "supersetColors",
        "order_desc": chart.get("order_desc", False),
    }
    if chart.get("time"):
        form_data.update(
            {
                "granularity_sqla": dataset.main_dttm_col,
                "time_grain_sqla": "P1D",
                "x_axis": dataset.main_dttm_col,
                "x_axis_time_format": "%Y-%m-%d",
            }
        )
    if chart.get("all_columns"):
        form_data["all_columns"] = chart["all_columns"]
        form_data["order_by_cols"] = [
            json.dumps([chart["order_by_cols"][0], False])
        ]
        form_data["row_limit"] = 100
    return form_data


def _chart_query_context(
    chart_spec: dict[str, Any],
    chart: Slice,
    dataset: SqlaTable,
) -> dict[str, Any]:
    form_data = json.loads(chart.params)
    is_timeseries = bool(chart_spec.get("time"))
    columns = list(form_data.get("groupby", []))
    if chart_spec.get("all_columns"):
        columns = list(chart_spec["all_columns"])

    metrics = form_data.get("metrics", [])
    if chart_spec.get("order_by_cols"):
        orderby = [[chart_spec["order_by_cols"][0], False]]
    elif chart_spec.get("order_desc") and metrics:
        orderby = [[metrics[0], False]]
    else:
        orderby = []
    query: dict[str, Any] = {
        "columns": columns,
        "metrics": metrics,
        "filters": [],
        "orderby": orderby,
        "row_limit": form_data.get("row_limit", 1000),
        "order_desc": chart_spec.get("order_desc", False),
        "is_timeseries": is_timeseries,
        "time_range": "No filter",
    }
    if is_timeseries:
        query["granularity"] = dataset.main_dttm_col

    return {
        "datasource": {"id": dataset.id, "type": "table"},
        "queries": [query],
        "result_format": "json",
        "result_type": "full",
        "form_data": form_data,
    }


def _upsert_chart(
    chart_spec: dict[str, Any],
    datasets: dict[str, SqlaTable],
) -> Slice:
    dataset = datasets[chart_spec["dataset"]]
    chart = (
        db.session.query(Slice)
        .filter_by(slice_name=chart_spec["name"])
        .one_or_none()
    )
    if chart is None:
        chart = Slice(slice_name=chart_spec["name"])
    chart.datasource_id = dataset.id
    chart.datasource_type = "table"
    chart.datasource_name = dataset.table_name
    chart.viz_type = chart_spec["viz_type"]
    chart.params = json.dumps(_chart_form_data(chart_spec, dataset))
    chart.query_context = json.dumps(
        _chart_query_context(chart_spec, chart, dataset)
    )
    chart.description = chart_spec["description"]
    db.session.add(chart)
    db.session.flush()
    return chart


def _dashboard_layout(charts: list[Slice]) -> dict[str, Any]:
    layout: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {
            "id": "ROOT_ID",
            "type": "ROOT",
            "children": ["GRID_ID"],
        },
        "GRID_ID": {
            "id": "GRID_ID",
            "type": "GRID",
            "children": [],
            "parents": ["ROOT_ID"],
        },
    }
    for index in range(0, len(charts), 2):
        row_id = f"ROW-{index // 2 + 1}"
        chart_ids = [
            f"CHART-{chart.id}" for chart in charts[index : index + 2]
        ]
        layout["GRID_ID"]["children"].append(row_id)
        layout[row_id] = {
            "id": row_id,
            "type": "ROW",
            "children": chart_ids,
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        for chart in charts[index : index + 2]:
            layout[f"CHART-{chart.id}"] = {
                "id": f"CHART-{chart.id}",
                "type": "CHART",
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {
                    "chartId": chart.id,
                    "width": 6,
                    "height": 50,
                },
            }
    return layout


def _dashboard_metadata() -> dict[str, Any]:
    return {
        "timed_refresh_immune_slices": [],
        "filter_scopes": {},
        "expanded_slices": {},
        "refresh_frequency": 0,
        "color_scheme": "supersetColors",
        "label_colors": {},
        "shared_label_colors": {},
        "cross_filters_enabled": True,
        "native_filter_configuration": [
            {
                "id": f"NATIVE_FILTER-{uuid.uuid4()}",
                "controlValues": {
                    "enableEmptyFilter": False,
                    "defaultToFirstItem": False,
                    "multiSelect": False,
                    "searchAllOptions": False,
                    "inverseSelection": False,
                },
                "name": "Date range",
                "filterType": "filter_time",
                "targets": [],
                "defaultDataMask": {
                    "extraFormData": {"time_range": "Last 90 days"},
                    "filterState": {
                        "value": "Last 90 days",
                        "label": "Last 90 days",
                    },
                },
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                "type": "NATIVE_FILTER",
            }
        ],
    }


def _upsert_dashboard(
    title: str,
    chart_names: list[str],
    chart_by_name: dict[str, Slice],
) -> Dashboard:
    dashboard = (
        db.session.query(Dashboard)
        .filter_by(dashboard_title=title)
        .one_or_none()
    )
    if dashboard is None:
        dashboard = Dashboard(dashboard_title=title)

    charts = [chart_by_name[name] for name in chart_names]
    dashboard.description = (
        f"{SIMULATED} This dashboard is generated from PlantPulse SQL "
        "datasets. Values are not live factory measurements."
    )
    dashboard.position_json = json.dumps(_dashboard_layout(charts))
    dashboard.json_metadata = json.dumps(_dashboard_metadata())
    dashboard.published = True
    dashboard.slices = charts
    db.session.add(dashboard)
    db.session.flush()
    return dashboard


def _validate_dataset(dataset: SqlaTable) -> int:
    database = dataset.database
    with database.get_sqla_engine() as engine:
        with engine.connect() as connection:
            result = connection.execute(
                text(f"SELECT * FROM ({dataset.sql}) AS plantpulse_dataset LIMIT 1")
            )
            columns = set(result.keys())
            row_count = connection.execute(
                text(f"SELECT COUNT(*) FROM ({dataset.sql}) AS plantpulse_dataset")
            ).scalar_one()
    expected = {column.column_name for column in dataset.columns}
    if columns != expected:
        raise RuntimeError(
            f"Dataset {dataset.table_name} metadata differs from SQL output."
        )
    if row_count == 0:
        raise RuntimeError(f"Dataset {dataset.table_name} returned no rows.")
    return row_count


def _validate_chart(chart_spec: dict[str, Any], chart: Slice) -> int:
    dataset = chart.table
    form_data = json.loads(chart.params)
    metric_expressions = {
        metric.metric_name: metric.expression for metric in dataset.metrics
    }
    selected_metrics = form_data.get("metrics", [])
    unknown_metrics = set(selected_metrics) - set(metric_expressions)
    if unknown_metrics:
        raise RuntimeError(
            f"Chart {chart.slice_name} references unknown metrics: "
            f"{sorted(unknown_metrics)}"
        )

    dimensions = list(form_data.get("groupby", []))
    if chart_spec.get("time"):
        dimensions.append(dataset.main_dttm_col)
    if chart_spec.get("all_columns"):
        dimensions = list(chart_spec["all_columns"])

    known_columns = {column.column_name for column in dataset.columns}
    unknown_columns = set(dimensions) - known_columns
    if unknown_columns:
        raise RuntimeError(
            f"Chart {chart.slice_name} references unknown columns: "
            f"{sorted(unknown_columns)}"
        )

    select_parts = [f'"{column}"' for column in dimensions]
    if not chart_spec.get("all_columns"):
        select_parts.extend(
            f'{metric_expressions[metric]} AS "{metric}"'
            for metric in selected_metrics
        )
    if not select_parts:
        select_parts.append("COUNT(*) AS row_count")
    query = (
        "SELECT "
        + ", ".join(select_parts)
        + f' FROM ({dataset.sql}) AS "plantpulse_chart_source"'
    )
    if dimensions and not chart_spec.get("all_columns"):
        query += " GROUP BY " + ", ".join(f'"{column}"' for column in dimensions)
    if chart_spec.get("order_desc") and selected_metrics:
        metric = selected_metrics[0]
        query += f' ORDER BY "{metric}" DESC'
    query += " LIMIT 5"
    with dataset.database.get_sqla_engine() as engine:
        with engine.connect() as connection:
            result = connection.execute(text(query))
            rows = result.fetchall()
    if not rows:
        raise RuntimeError(f"Chart {chart.slice_name} returned no rows.")
    return len(rows)


def _validate_rendered_charts(
    chart_specs: dict[str, dict[str, Any]],
    application: Any,
) -> None:
    from flask import g
    from flask_login import login_user

    from superset import security_manager
    from superset.charts.schemas import ChartDataQueryContextSchema
    from superset.commands.chart.data.get_data_command import ChartDataCommand

    admin_role = security_manager.find_role("Admin")
    if admin_role is None:
        raise RuntimeError(
            "The Superset Admin role is missing. Run the documented "
            "Superset initialization before provisioning dashboards."
        )
    validator = security_manager.add_user(
        username=f"plantpulse_chart_validator_{secrets.token_hex(8)}",
        first_name="Temporary",
        last_name="Chart Validator",
        email=f"chart-validator-{secrets.token_hex(8)}@example.invalid",
        role=admin_role,
        password=secrets.token_urlsafe(32),
    )
    if validator is None:
        raise RuntimeError("Could not create the temporary chart validator.")

    try:
        with application.test_request_context("/"):
            login_user(validator)
            g.user = validator
            charts = db.session.query(Slice).order_by(Slice.id).all()
            for chart in charts:
                if chart.slice_name not in chart_specs:
                    continue
                if not chart.query_context:
                    raise RuntimeError(
                        f"Chart {chart.slice_name} has no saved query context."
                    )
                query_context = ChartDataQueryContextSchema().load(
                    json.loads(chart.query_context)
                )
                command = ChartDataCommand(query_context)
                command.validate()
                response = command.run()
                queries = response["queries"]
                if (
                    not queries
                    or queries[0].get("error")
                    or not queries[0].get("data")
                ):
                    raise RuntimeError(
                        f"Superset returned no chart data for {chart.slice_name}."
                    )
                print(
                    f"RENDER {chart.slice_name}: "
                    f"{len(queries[0]['data'])} rows"
                )
    finally:
        db.session.delete(validator)
        db.session.commit()
        print("Temporary chart-validation account removed")


def provision(application: Any) -> None:
    database = (
        db.session.query(Database).filter_by(database_name="PlantPulse").one_or_none()
    )
    if database is None:
        raise RuntimeError(
            "Register the PostgreSQL database as 'PlantPulse' in Superset first."
        )

    with database.get_sqla_engine() as engine:
        with engine.connect() as connection:
            current_database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()
    if current_database != "plantpulse":
        raise RuntimeError(
            "The registered PlantPulse connection does not point to "
            f"the expected database (got {current_database!r})."
        )

    datasets = {
        name: _upsert_dataset(database, name, spec)
        for name, spec in DATASETS.items()
    }
    db.session.flush()

    dataset_rows = {
        name: _validate_dataset(dataset) for name, dataset in datasets.items()
    }
    chart_specs = {chart["name"]: chart for chart in CHARTS}
    charts = {
        chart["name"]: _upsert_chart(chart, datasets) for chart in CHARTS
    }
    db.session.flush()

    chart_rows = {
        name: _validate_chart(chart_specs[name], chart)
        for name, chart in charts.items()
    }
    dashboards = {
        title: _upsert_dashboard(title, names, charts)
        for title, names in DASHBOARDS.items()
    }
    db.session.commit()

    _validate_rendered_charts(
        {chart["name"]: chart for chart in CHARTS},
        application,
    )

    for name, row_count in dataset_rows.items():
        print(f"DATASET {name}: validated {row_count} rows")
    for name, row_count in chart_rows.items():
        print(f"CHART {name}: validated sample query returned {row_count} rows")
    for title, dashboard in dashboards.items():
        print(
            f"DASHBOARD {title}: id={dashboard.id}, "
            f"charts={len(dashboard.slices)}, published={dashboard.published}"
        )


def main() -> None:
    from superset.app import create_app

    app = create_app()
    with app.app_context():
        global db, Database, Dashboard, Slice, SqlMetric, SqlaTable, TableColumn

        from superset import db
        from superset.connectors.sqla.models import (
            SqlMetric,
            SqlaTable,
            TableColumn,
        )
        from superset.models.core import Database
        from superset.models.dashboard import Dashboard
        from superset.models.slice import Slice

        provision(app)


if __name__ == "__main__":
    main()
