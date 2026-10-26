"""PostgreSQL connectivity and query helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DatabaseUnavailableError(RuntimeError):
    """Raised when PostgreSQL configuration or connectivity is unavailable."""


def _connection_settings() -> dict[str, str | int]:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return {
            "conninfo": database_url,
            "connect_timeout": 5,
        }

    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise DatabaseUnavailableError(
            "Missing required database configuration: " + ", ".join(missing)
        )
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "connect_timeout": 5,
    }


def fetch_all(query: str) -> list[dict[str, Any]]:
    """Execute a read-only query and return rows as dictionaries."""
    try:
        with psycopg.connect(**_connection_settings(), row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return list(cursor.fetchall())
    except (psycopg.Error, OSError) as error:
        raise DatabaseUnavailableError(
            "The database request could not be completed."
        ) from error
