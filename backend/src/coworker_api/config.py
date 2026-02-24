"""
Configuration management for Edtronaut AI Coworker.

Loads settings from environment variables and YAML config files
using pydantic-settings for type-safe configuration.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve paths
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent
_CONFIGS_DIR = _BACKEND_DIR / "configs"

# Load .env for local runs. Docker compose env vars still win.
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=False)
load_dotenv(dotenv_path=_BACKEND_DIR / ".env", override=False)


def _load_yaml_config(filename: str = "default.yml") -> dict:
    """Load a YAML configuration file and return as dict."""
    config_path = _CONFIGS_DIR / filename
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _normalize_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


class LLMSettings(BaseModel):
    provider: str = "openai"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    streaming: bool = True


class EmbeddingSettings(BaseModel):
    provider: str = "openai"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    dimensions: int = 1536
    fallback_provider: str = ""


class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 1800


class PostgresSettings(BaseModel):
    url: str = "postgresql+asyncpg://edtronaut:edtronaut@localhost:5432/edtronaut"
    run_migrations_on_startup: bool = True
    bootstrap_schema_on_startup: bool = False


class QdrantSettings(BaseModel):
    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    collection_name: str = "knowledge_base"


class GRPCSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 50051


class RESTSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class RAGSettings(BaseModel):
    enabled: bool = True


class AuthSettings(BaseModel):
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15


class LangfuseSettings(BaseModel):
    enabled: bool = False
    public_key: str = ""
    secret_key: str = ""
    host: str = "https://cloud.langfuse.com"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    with fallback to configs/default.yml values.

    Env vars use nested delimiter "__", e.g.:
      REDIS__URL=redis://redis:6379/0
      LLM__PROVIDER=gemini
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        env_file=(str(_PROJECT_ROOT / ".env"), str(_BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
    )

    # App
    app_name: str = "edtronaut-ai-coworker"
    app_version: str = "0.1.0"
    debug: bool = False

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    grpc: GRPCSettings = Field(default_factory=GRPCSettings)
    rest: RESTSettings = Field(default_factory=RESTSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton factory for application settings.

    Priority: Environment Variables > YAML config > Defaults.

    We manually override YAML values with Environment variables matching the
    SECTION__FIELD pattern (e.g. REDIS__URL) to ensure Docker environment
    variables always take precedence over YAML defaults (like localhost).
    """
    yaml_config = _load_yaml_config("default.yml")

    # 1. Collect environment variable overrides (SECTION__FIELD)
    env_overrides: dict[str, dict[str, str]] = {}
    for key, value in os.environ.items():
        if "__" not in key:
            continue

        parts = key.lower().split("__", 1)
        if len(parts) != 2:
            continue

        section, field = parts
        env_overrides.setdefault(section, {})
        env_overrides[section][field] = _normalize_env_value(value)

    # 1b. Compatibility for flat Langfuse env vars shown in Langfuse dashboard docs.
    langfuse_compat_map = {
        "LANGFUSE_PUBLIC_KEY": "public_key",
        "LANGFUSE_SECRET_KEY": "secret_key",
        "LANGFUSE_BASE_URL": "host",
        "LANGFUSE_HOST": "host",
        "LANGFUSE_ENABLED": "enabled",
    }
    for env_key, field in langfuse_compat_map.items():
        raw_value = os.getenv(env_key)
        if raw_value is None:
            continue
        value = _normalize_env_value(raw_value)
        if value == "":
            continue

        env_overrides.setdefault("langfuse", {})
        # Preserve explicit nested vars if both are present.
        env_overrides["langfuse"].setdefault(field, value)

    # 2. Merge Env overrides into YAML configuration
    for section, fields in env_overrides.items():
        if section == "app":
            yaml_config.setdefault("app", {}).update(fields)
        else:
            yaml_config.setdefault(section, {}).update(fields)

    # 3. Flatten YAML into constructor arguments for Settings
    overrides: dict = {}
    for section_key, section_val in yaml_config.items():
        if isinstance(section_val, dict):
            if section_key == "app":
                for k, v in section_val.items():
                    if k == "debug":
                        overrides["debug"] = v
                    else:
                        overrides[f"app_{k}"] = v
            else:
                overrides[section_key] = section_val
        else:
            overrides[section_key] = section_val

    return Settings(**overrides)


def load_npc_config(filename: str = "npc_gucci.yml") -> dict:
    """Load NPC persona configurations from YAML."""
    return _load_yaml_config(filename)
