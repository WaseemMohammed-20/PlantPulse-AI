"""Authentication behavior for protected API endpoints."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import auth, database
from app.main import app

ISSUER = "https://plantpulse.example.clerk.accounts.dev"
AUTHORIZED_PARTY = "http://127.0.0.1:5173"
AUDIENCE = "plantpulse-api"


def request(path: str, token: str | None = None) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            return await client.get(path, headers=headers)

    return asyncio.run(send_request())


def preflight(path: str, origin: str, requested_headers: str) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.options(
                path,
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": requested_headers,
                },
            )

    return asyncio.run(send_request())


@pytest.fixture
def signing_keys() -> tuple[Any, Any]:
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
    )


@pytest.fixture
def clerk_settings(monkeypatch: pytest.MonkeyPatch, signing_keys: tuple[Any, Any]) -> Any:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("CLERK_ISSUER", ISSUER)
    monkeypatch.setenv("CLERK_JWKS_URL", f"{ISSUER}/.well-known/jwks.json")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", AUTHORIZED_PARTY)
    monkeypatch.setenv("CLERK_AUDIENCE", AUDIENCE)

    class TestJwksClient:
        def get_signing_key_from_jwt(self, _token: str) -> Any:
            return type("SigningKey", (), {"key": signing_keys[0].public_key()})()

    monkeypatch.setattr(auth, "_get_jwks_client", lambda _url: TestJwksClient())
    monkeypatch.setattr(database, "fetch_all", lambda _query: [])
    return signing_keys


def make_token(
    private_key: Any,
    *,
    expires_at: datetime | None = None,
    issuer: str = ISSUER,
    authorized_party: str = AUTHORIZED_PARTY,
    audience: str = AUDIENCE,
) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "iss": issuer,
            "sub": "user_test_123",
            "azp": authorized_party,
            "aud": audience,
            "iat": now,
            "nbf": now - timedelta(seconds=1),
            "exp": expires_at or now + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


@pytest.mark.parametrize(
    "path",
    (
        "/api/overview",
        "/api/production/trends",
        "/api/production/lines",
        "/api/downtime/causes",
        "/api/downtime/machines",
        "/api/quality/lines",
        "/api/machines",
    ),
)
def test_protected_endpoint_rejects_missing_token(
    clerk_settings: tuple[Any, Any],
    path: str,
) -> None:
    response = request(path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("token", ("not-a-jwt", "Bearer invalid.token.value"))
def test_protected_endpoint_rejects_malformed_token(
    clerk_settings: tuple[Any, Any],
    token: str,
) -> None:
    response = request("/api/production/trends", token)

    assert response.status_code == 401


def test_protected_endpoint_rejects_expired_token(
    clerk_settings: tuple[Any, Any],
    signing_keys: tuple[Any, Any],
) -> None:
    token = make_token(
        signing_keys[0],
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    response = request("/api/production/trends", token)

    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_signature(
    clerk_settings: tuple[Any, Any],
    signing_keys: tuple[Any, Any],
) -> None:
    token = make_token(signing_keys[1])

    response = request("/api/production/trends", token)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "claims",
    (
        {"issuer": "https://wrong-issuer.example"},
        {"authorized_party": "https://untrusted.example"},
        {"audience": "another-api"},
    ),
)
def test_protected_endpoint_rejects_invalid_claims(
    clerk_settings: tuple[Any, Any],
    signing_keys: tuple[Any, Any],
    claims: dict[str, str],
) -> None:
    token = make_token(signing_keys[0], **claims)

    response = request("/api/production/trends", token)

    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_clerk_session_token(
    clerk_settings: tuple[Any, Any],
) -> None:
    private_key, _ = clerk_settings
    token = make_token(private_key)

    response = request("/api/production/trends", token)

    assert response.status_code == 200
    assert response.json() == []


def test_health_endpoint_remains_public_when_authentication_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setattr(database, "fetch_all", lambda _query: [{"connected": 1}])

    response = request("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_cors_allows_authorization_header_from_local_frontend() -> None:
    response = preflight(
        "/api/production/trends",
        origin=AUTHORIZED_PARTY,
        requested_headers="authorization",
    )

    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_production_authentication_requires_clerk_verification_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTH_REQUIRED", raising=False)
    for name in (
        "CLERK_ISSUER",
        "CLERK_JWKS_URL",
        "CLERK_AUTHORIZED_PARTIES",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="Authentication requires"):
        auth.validate_auth_configuration()


def test_production_authentication_cannot_be_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_REQUIRED", "false")

    with pytest.raises(RuntimeError, match="only be disabled"):
        auth.validate_auth_configuration()
