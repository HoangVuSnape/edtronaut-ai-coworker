"""
Shared password hashing — single CryptContext instance.

Used by rest_routes, grpc_server, and postgres_store.
"""

from passlib.context import CryptContext

# Single shared instance for the entire backend.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
