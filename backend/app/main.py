"""PlantPulse AI FastAPI application."""

import os
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.auth import require_authenticated_user, validate_auth_configuration
from app.routers import downtime, health, machines, overview, production, quality

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

load_dotenv(PROJECT_ROOT / ".env")
validate_auth_configuration()


def _get_cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ORIGINS", "")
    if not configured_origins.strip():
        environment = os.getenv("APP_ENV", "development").strip().lower()
        if environment and environment != "development":
            raise RuntimeError("CORS_ORIGINS must be set outside development.")
        return list(DEFAULT_CORS_ORIGINS)

    origins = list(
        dict.fromkeys(
            origin.strip().rstrip("/")
            for origin in configured_origins.split(",")
            if origin.strip()
        )
    )
    if "*" in origins:
        raise ValueError("CORS_ORIGINS must contain explicit trusted origins.")
    return origins


app = FastAPI(
    title="PlantPulse AI API",
    description="Manufacturing performance and quality analytics API.",
    version="0.1.0",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)

app.include_router(health.router, prefix="/api")

for router in (
    overview.router,
    production.router,
    downtime.router,
    quality.router,
    machines.router,
):
    app.include_router(
        router,
        prefix="/api",
        dependencies=[Depends(require_authenticated_user)],
    )
