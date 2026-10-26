"""Automated tests for PlantPulse AI API response behavior."""

import asyncio
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import database  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def local_demo_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_REQUIRED", "false")


def request(
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, headers=headers)

    return asyncio.run(send_request())


def set_rows(monkeypatch: Any, rows: list[dict[str, Any]]) -> None:
    monkeypatch.setattr(database, "fetch_all", lambda _query: rows)


def test_database_url_takes_precedence_over_postgres_fields(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo:demo@localhost/demo")
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    settings = database._connection_settings()

    assert settings == {
        "conninfo": "postgresql://demo:demo@localhost/demo",
        "connect_timeout": 5,
    }


def test_health_reports_database_connection(monkeypatch: Any) -> None:
    set_rows(monkeypatch, [{"connected": 1}])

    response = request("GET", "/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_returns_service_unavailable_for_database_error(
    monkeypatch: Any,
) -> None:
    def fail(_query: str) -> list[dict[str, Any]]:
        raise database.DatabaseUnavailableError("private connection detail")

    monkeypatch.setattr(database, "fetch_all", fail)
    response = request("GET", "/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"status": "unavailable", "database": "disconnected"}
    }
    assert "private connection detail" not in response.text


def test_overview_returns_database_derived_metrics(monkeypatch: Any) -> None:
    set_rows(
        monkeypatch,
        [
            {
                "production_quantity": 120,
                "production_target": 150,
                "target_attainment_pct": 80.0,
                "oee_pct": 75.0,
                "unplanned_downtime_minutes": 12.5,
                "inspected_units": 40,
                "defective_units": 2,
                "defect_rate_pct": 5.0,
            }
        ],
    )

    response = request("GET", "/api/overview")

    assert response.status_code == 200
    assert response.json()["production_quantity"] == 120
    assert response.json()["target_attainment_pct"] == 80.0


def test_all_analytics_endpoints_return_typed_rows(monkeypatch: Any) -> None:
    payloads = (
        (
            "/api/production/trends",
            {
                "production_date": "2026-10-24",
                "production_quantity": 100,
                "good_quantity": 96,
                "production_target": 120,
            },
        ),
        (
            "/api/production/lines",
            {
                "line_id": 1,
                "line_code": "LINE-01",
                "line_name": "Assembly",
                "factory_name": "Plant",
                "production_quantity": 100,
                "production_target": 120,
                "target_attainment_pct": 83.33,
                "unplanned_downtime_minutes": 10.0,
            },
        ),
        (
            "/api/downtime/causes",
            {
                "cause": "equipment_failure",
                "is_planned": False,
                "event_count": 2,
                "downtime_minutes": 14.0,
            },
        ),
        (
            "/api/downtime/machines",
            {
                "downtime_rank": 1,
                "machine_id": 2,
                "machine_code": "M-01",
                "machine_name": "Press",
                "production_line": "Assembly",
                "factory_name": "Plant",
                "unplanned_event_count": 2,
                "unplanned_downtime_minutes": 14.0,
            },
        ),
        (
            "/api/quality/lines",
            {
                "line_id": 1,
                "line_code": "LINE-01",
                "line_name": "Assembly",
                "factory_name": "Plant",
                "inspected_units": 40,
                "defective_units": 2,
                "defect_rate_pct": 5.0,
            },
        ),
        (
            "/api/machines",
            {
                "machine_id": 2,
                "machine_code": "M-01",
                "machine_name": "Press",
                "machine_type": "hydraulic_press",
                "rated_capacity_per_hour": 64.0,
                "line_id": 1,
                "line_code": "LINE-01",
                "line_name": "Assembly",
                "factory_id": 1,
                "factory_name": "Plant",
                "production_quantity": 100,
                "production_target": 120,
                "target_attainment_pct": 83.33,
                "unplanned_downtime_minutes": 10.0,
                "inspected_units": 40,
                "defective_units": 2,
                "defect_rate_pct": 5.0,
            },
        ),
    )

    for path, payload in payloads:
        set_rows(monkeypatch, [payload])
        response = request("GET", path)
        assert response.status_code == 200, path
        assert response.json() == [payload], path


def test_empty_analytics_results_return_empty_arrays(monkeypatch: Any) -> None:
    set_rows(monkeypatch, [])

    for path in (
        "/api/production/trends",
        "/api/production/lines",
        "/api/downtime/causes",
        "/api/downtime/machines",
        "/api/quality/lines",
        "/api/machines",
    ):
        response = request("GET", path)
        assert response.status_code == 200, path
        assert response.json() == [], path


def test_cors_allows_both_local_frontend_origins() -> None:
    allowed_origins = ("http://localhost:5173", "http://127.0.0.1:5173")
    for origin in allowed_origins:
        allowed = request(
            "OPTIONS",
            "/api/health",
            {
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert allowed.headers["access-control-allow-origin"] == origin

    denied = request(
        "OPTIONS",
        "/api/health",
        {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in denied.headers


def test_cors_origins_use_environment_configuration(monkeypatch: Any) -> None:
    from app.main import _get_cors_origins

    monkeypatch.setenv("CORS_ORIGINS", "https://plantpulse.example, https://admin.example/")

    assert _get_cors_origins() == [
        "https://plantpulse.example",
        "https://admin.example",
    ]
