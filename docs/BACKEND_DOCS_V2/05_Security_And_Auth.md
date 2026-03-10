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
- `auth.supabase_jwt_secret` (Used to verify external Supabase login tokens)

## Supabase & External Auth

The system actively supports external authentication providers like Google (Gmail) via **Supabase**. See the detailed plan in `docs/BACKEND_DOCS_V2/11_Supabase_Gmail_Login.md`.

- The frontend manages the OAuth layer and passes the resulting Supabase JWT to the backend.
- The FASTAPI backend verifies the token using the `auth.supabase_jwt_secret`.
- If an externally authenticated user (from Supabase) is not yet in the backend PostgreSQL DB, the `_ensure_chat_session` method handles auto-creating the basic user record securely.

## Hardening ideas (not implemented)

- Refresh tokens.
- Login rate limiting.
- JWT rotation and key management.
- TLS enforced in production.
