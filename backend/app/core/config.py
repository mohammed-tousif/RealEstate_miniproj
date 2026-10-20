"""Application settings, read from environment variables (or a .env file).

Secrets are never hardcoded. In development a missing JWT secret is replaced by a
random per-process value (tokens then stop working after a restart); in
production a missing secret is a startup error.
"""
from __future__ import annotations

import logging
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, PrivateAttr, field_validator
from typing import Annotated

from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent

log = logging.getLogger("propwise.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", description="development | test | production")
    app_name: str = "PropWise AI"

    # SQLite keeps the zero-install demo working; set a postgresql+psycopg:// URL for PostgreSQL.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'propwise.db').as_posix()}"

    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    bcrypt_rounds: int = 12

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    storage_dir: Path = BACKEND_DIR / "storage"
    max_upload_mb: int = 5
    max_images_per_property: int = 10

    # No authorised document-verification process exists in this prototype, so
    # the "verified" document status cannot be set unless this is switched on.
    document_verification_process_enabled: bool = False

    # Trained price model (scripts/train_price_model.py writes here).
    price_model_dir: Path = REPO_DIR / "ml" / "artifacts" / "price_model"

    # Karnataka bounding box used to sanity-check coordinates for this deployment.
    geo_lat_min: float = 11.5
    geo_lat_max: float = 18.5
    geo_lng_min: float = 74.0
    geo_lng_max: float = 78.6

    # Chat assistant (M5). Without a key the assistant runs in the labelled rule-based Basic search mode.
    anthropic_api_key: str | None = Field(default=None, validation_alias=AliasChoices("ANTHROPIC_API_KEY",
                                                                                      "LLM_API_KEY"))
    llm_model: str = "claude-opus-5-5"
    llm_effort: str = "low"
    llm_max_tokens: int = 16000
    llm_timeout_seconds: float = 60.0
    llm_max_tool_rounds: int = 5
    # Requests per client per minute on /ai/chat. Behind a trusted proxy (the Next.js server on Render)
    # the client address is read from X-Forwarded-For.
    ai_rate_limit_per_minute: int = 12
    trust_proxy_headers: bool = False
    login_failures_per_minute: int = 10

    _dev_secret: str | None = PrivateAttr(default=None)

    @field_validator("database_url", mode="before")
    @classmethod
    def _psycopg_driver(cls, v):
        # Render and most hosts hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the psycopg 3 driver name.
        if isinstance(v, str):
            for prefix in ("postgres://", "postgresql://"):
                if v.startswith(prefix):
                    return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str) and not v.strip().startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def llm_configured(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def resolved_jwt_secret(self) -> str:
        if self.jwt_secret:
            return self.jwt_secret
        if self.is_production:
            raise RuntimeError("JWT_SECRET must be set in production")
        if self._dev_secret is None:
            log.warning("JWT_SECRET not set; using a random development secret (tokens reset on restart)")
            self._dev_secret = secrets.token_urlsafe(48)
        return self._dev_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
