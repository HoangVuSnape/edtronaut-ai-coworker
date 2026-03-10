"""
Shared JWT authentication logic.

Centralises token decoding, JWKS fetching, and Supabase JWT
verification so that both REST (FastAPI) and gRPC layers import
from a single source of truth.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from jose import JWTError, jwt

from coworker_api.config import get_settings

logger = logging.getLogger(__name__)

# ── JWKS Cache ──

_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_JWKS_TTL_SECONDS = 3600


# ── Public API ──


def decode_jwt(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Supports:
    - Supabase-issued JWTs (RS256 / ES256 via JWKS, HS256 via secret)
    - Legacy self-issued JWTs (HS256 via jwt_secret_key)

    Returns the decoded payload dict on success.
    Raises ``ValueError`` on any verification failure.
    """
    settings = get_settings()
    allowed_algorithms = get_allowed_jwt_algorithms(settings)
    header_alg = get_token_alg(token)

    # Supabase JWT verification path
    supabase_secret = settings.auth.supabase_jwt_secret.strip()
    if supabase_secret:
        try:
            if header_alg and header_alg.startswith(("RS", "ES")):
                jwks_urls = get_supabase_jwks_urls(token)
                jwk_key = get_jwks_key(jwks_urls, token)
                payload = jwt.decode(
                    token,
                    jwk_key,
                    algorithms=[header_alg],
                    audience="authenticated",
                )
            elif header_alg and header_alg not in allowed_algorithms:
                raise JWTError(
                    f"The specified alg value is not allowed: {header_alg}"
                )
            else:
                payload = jwt.decode(
                    token,
                    supabase_secret,
                    algorithms=allowed_algorithms,
                    audience="authenticated",
                )
        except JWTError as e:
            _log_jwt_decode_failure("supabase", token, allowed_algorithms, e)
            raise ValueError(f"Invalid or expired token: {e}")

        if not payload.get("sub"):
            raise ValueError("Invalid token payload: missing sub")

        # Extract role from app_metadata
        app_metadata = payload.get("app_metadata", {})
        role = (
            app_metadata.get("role", "user")
            if isinstance(app_metadata, dict)
            else "user"
        )
        payload["role"] = role
        return payload

    # Legacy self-issued JWT path
    secret = settings.auth.jwt_secret_key.strip()

    if not secret or secret == "CHANGE_ME_IN_PRODUCTION":
        raise ValueError("Authentication is not configured")

    try:
        payload = jwt.decode(token, secret, algorithms=allowed_algorithms)
    except JWTError as e:
        _log_jwt_decode_failure("legacy", token, allowed_algorithms, e)
        raise ValueError(f"Invalid or expired token: {e}")

    if not payload.get("sub"):
        raise ValueError("Invalid token payload: missing sub")

    return payload


# ── Helpers ──


def get_allowed_jwt_algorithms(settings) -> list[str]:
    raw = settings.auth.jwt_algorithm or ""
    parts = [part.strip().upper() for part in raw.split(",")]
    allowed = [part for part in parts if part]
    return allowed or ["HS256"]


def get_token_alg(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        return ""
    return str(header.get("alg", "")).upper()


def get_supabase_jwks_urls(token: str) -> list[str]:
    try:
        claims = jwt.get_unverified_claims(token)
    except Exception:
        claims = {}

    iss = str(claims.get("iss", "")).rstrip("/")
    supabase_url = (
        os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or ""
    )
    supabase_url = supabase_url.rstrip("/")

    base_url = ""
    if iss:
        if iss.endswith("/auth/v1"):
            base_url = iss[: -len("/auth/v1")]
        else:
            base_url = iss
    elif supabase_url:
        base_url = supabase_url

    if not base_url:
        raise ValueError("Supabase URL is not configured for JWKS lookup")

    return [
        f"{base_url}/auth/v1/keys",
        f"{base_url}/auth/v1/.well-known/jwks.json",
        f"{base_url}/.well-known/jwks.json",
    ]


def get_jwks_key(jwks_urls: list[str], token: str) -> dict[str, Any]:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    jwks = _fetch_jwks_any(jwks_urls)
    keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
    if keys:
        return keys[0]
    raise ValueError("No JWKS keys available for token verification")


def _fetch_jwks_any(jwks_urls: list[str]) -> dict[str, Any]:
    last_error: Exception | None = None
    for jwks_url in jwks_urls:
        try:
            return _fetch_jwks(jwks_url)
        except Exception as exc:
            last_error = exc
            continue
    if last_error is None:
        raise ValueError("Failed to fetch JWKS: no URLs provided")
    raise last_error


def _fetch_jwks(jwks_url: str) -> dict[str, Any]:
    now = time.time()
    cached = _JWKS_CACHE.get(jwks_url)
    if cached and now - cached[0] < _JWKS_TTL_SECONDS:
        return cached[1]

    headers: dict[str, str] = {}
    supabase_anon_key = (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("VITE_SUPABASE_ANON_KEY")
        or ""
    )
    if supabase_anon_key:
        headers["apikey"] = supabase_anon_key

    try:
        resp = httpx.get(jwks_url, headers=headers, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise ValueError(f"Failed to fetch JWKS: {exc}")

    _JWKS_CACHE[jwks_url] = (now, data)
    return data


def _log_jwt_decode_failure(
    path: str,
    token: str,
    allowed_algorithms: list[str],
    error: Exception,
) -> None:
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        header = {}

    try:
        claims = jwt.get_unverified_claims(token)
    except Exception:
        claims = {}

    alg = header.get("alg")
    kid = header.get("kid")
    iss = claims.get("iss")
    logger.error(
        "JWT decode failed (%s): alg=%s kid=%s iss=%s allowed=%s err=%s",
        path,
        alg,
        kid,
        iss,
        allowed_algorithms,
        error,
    )
