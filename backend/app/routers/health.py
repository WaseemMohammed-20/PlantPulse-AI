"""Health endpoint."""

from fastapi import APIRouter, HTTPException

from app import database
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        database.fetch_all("SELECT 1 AS connected")
    except database.DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "database": "disconnected"},
        ) from error
    return HealthResponse(status="ok", database="connected")
