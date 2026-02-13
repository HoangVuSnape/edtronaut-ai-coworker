"""
Configuration management for Edtronaut AI Coworker.

Loads settings from environment variables and YAML config files
using pydantic-settings for type-safe configuration.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Resolve paths ──
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
_CONFIGS_DIR = _BACKEND_DIR / "configs"


def _load_yaml_config(filename: str = "default.yml") -> dict:
    """Load a YAML configuration file and return as dict."""
    config_path = _CONFIGS_DIR / filename
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ── Sub-Models (using BaseModel for simple struct) ──

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


class AuthSettings(BaseModel):
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15


class LangfuseSettings(BaseModel):
    enabled: bool = False
    public_key: str = ""
    secret_key: str = ""
    host: str = "https://cloud.langfuse.com"


# ── Main Settings ──

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
        if "__" in key:
            # Only support 1 level of nesting: SECTION__FIELD
            parts = key.lower().split("__", 1)
            if len(parts) == 2:
                section, field = parts
                if section not in env_overrides:
                    env_overrides[section] = {}
                env_overrides[section][field] = value

    # 2. Merge Env overrides into YAML configuration
    for section, fields in env_overrides.items():
        if section == "app":
            # Special 'app' handling logic later, just store for now
            yaml_config.setdefault("app", {}).update(fields)
        else:
            # Create section if missing to ensure Env vars make it to Settings
            # (Settings will ignore if it's an unknown section due to extra="ignore")
            yaml_config.setdefault(section, {}).update(fields)

    # 3. Flatten YAML into constructor arguments for Settings
    #    (Pydantic V2 BaseSettings initialized with kwargs treats them as priority)
    overrides: dict = {}
    for section_key, section_val in yaml_config.items():
        if isinstance(section_val, dict):
            # Special handling: map "app" section to flat fields
            if section_key == "app":
                for k, v in section_val.items():
                    if k == "debug":
                        overrides["debug"] = v
                    else:
                        overrides[f"app_{k}"] = v
            else:
                # Pass nested dicts directly — matching sub-models
                overrides[section_key] = section_val
        else:
            overrides[section_key] = section_val

    return Settings(**overrides)


def load_npc_config(filename: str = "npc_gucci.yml") -> dict:
    """Load NPC persona configurations from YAML."""
    return _load_yaml_config(filename)
