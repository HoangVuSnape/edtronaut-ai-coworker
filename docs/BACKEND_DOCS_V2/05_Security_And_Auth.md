# Security and Authentication

## Current state

Auth is implemented on REST in `backend/src/coworker_api/infrastructure/api/rest_routes.py`. gRPC auth interceptors are not implemented yet.

## JWT flow

- Login: `POST /api/auth/login`.
- JWT is created using `python-jose` with `HS256`.
- Client sends `Authorization: Bearer <token>`.
- Token claims: `sub`, `email`, `role`, `iat`, `exp`.

## Authorization rules

- `require_authenticated` validates JWT and payload.
- `require_admin` enforces admin role.
- `_ensure_user_access` ensures users only access their own sessions.

Admin-only routes:

- CRUD for Users, NPCs, Scenarios.

Authenticated routes:

- Session list, get session, delete session.
- Chat endpoint.

## Password hashing

- `passlib` with `pbkdf2_sha256` and `bcrypt` (bcrypt for backward verification).
- Minimum length: 8 characters.

## Auth configuration

File: `backend/src/coworker_api/config.py`

- `auth.jwt_secret_key`
- `auth.jwt_algorithm`
- `auth.access_token_expire_minutes`

## Hardening ideas (not implemented)

- Refresh tokens.
- Login rate limiting.
- JWT rotation and key management.
- TLS enforced in production.
