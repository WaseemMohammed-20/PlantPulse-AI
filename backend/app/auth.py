"""Clerk session-token verification for protected API routes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class AuthSettings:
    required: bool
    issuer: str | None
    jwks_url: str | None
    authorized_parties: tuple[str, ...]
    audience: str | None


def get_auth_settings() -> AuthSettings:
    environment = os.getenv("APP_ENV", "development").strip().lower() or "development"
    required_value = os.getenv("AUTH_REQUIRED")
    required = (
        required_value.strip().lower() in {"1", "true", "yes", "on"}
        if required_value is not None
        else environment != "development"
    )
    if required_value is not None and required_value.strip().lower() not in {
        "0",
        "1",
        "false",
        "true",
        "no",
        "yes",
        "off",
        "on",
    }:
        raise RuntimeError("AUTH_REQUIRED must be a boolean value.")
    if environment != "development" and not required:
        raise RuntimeError(
            "Authentication can only be disabled when APP_ENV=development."
        )

    parties = tuple(
        dict.fromkeys(
            party.strip().rstrip("/")
            for party in os.getenv("CLERK_AUTHORIZED_PARTIES", "").split(",")
            if party.strip()
        )
    )
    settings = AuthSettings(
        required=required,
        issuer=os.getenv("CLERK_ISSUER", "").strip() or None,
        jwks_url=os.getenv("CLERK_JWKS_URL", "").strip() or None,
        authorized_parties=parties,
        audience=os.getenv("CLERK_AUDIENCE", "").strip() or None,
    )
    if required and (
        not all((settings.issuer, settings.jwks_url))
        or not settings.authorized_parties
    ):
        raise RuntimeError(
            "Authentication requires CLERK_ISSUER, CLERK_JWKS_URL, "
            "and CLERK_AUTHORIZED_PARTIES."
        )
    return settings


def validate_auth_configuration() -> None:
    get_auth_settings()


@lru_cache(maxsize=4)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, timeout=5)


def require_authenticated_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    settings = get_auth_settings()
    if not settings.required:
        return {"sub": "local-demo-user"}

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        signing_key = _get_jwks_client(settings.jwks_url).get_signing_key_from_jwt(
            token.strip()
        )
        payload = jwt.decode(
            token.strip(),
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.issuer,
            audience=settings.audience,
            options={
                "require": ["exp", "iss", "sub"],
                "verify_aud": settings.audience is not None,
            },
        )
        authorized_party = payload.get("azp")
        if (
            not isinstance(authorized_party, str)
            or authorized_party.rstrip("/") not in settings.authorized_parties
        ):
            raise jwt.InvalidTokenError("Invalid authorized party.")
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise jwt.InvalidTokenError("Missing subject.")
    except PyJWKClientConnectionError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider keys are temporarily unavailable.",
        ) from error
    except (PyJWTError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return payload
