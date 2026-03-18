from pathlib import Path
import json
import re
from typing import Annotated
from typing import Literal
import warnings

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(BACKEND_DIR / ".env"),
            str(REPO_ROOT / ".env"),
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "DataSim Lab API"
    api_prefix: str = "/api/v1"
    app_env: Literal["development", "staging", "production"] = "development"

    mongodb_uri: str = Field(validation_alias="MONGODB_URI")
    mongodb_database: str = Field(
        default="datasim_lab",
        validation_alias="MONGODB_DATABASE",
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    artifacts_dir: str = "artifacts"
    generation_chunk_size: int = 100000
    generation_min_chunk_size: int = 10000
    generation_target_cells_per_chunk: int = 1500000
    async_generation_row_threshold: int = 50000
    async_generation_cell_threshold: int = 1000000
    quality_alert_threshold: int = 5
    artifact_retention_hours: int = 24
    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    redis_url: str = Field(default="", validation_alias="REDIS_URL")
    celery_broker_url: str = Field(default="", validation_alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="",
        validation_alias="CELERY_RESULT_BACKEND",
    )
    async_generation_enabled: bool = Field(
        default=False,
        validation_alias="ASYNC_GENERATION_ENABLED",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str] | object:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if not isinstance(value, str):
            return value

        raw = value.strip()
        if not raw:
            return []

        # Accept JSON arrays and shell-wrapped JSON strings.
        wrapped = (raw.startswith('"') and raw.endswith('"')) or (
            raw.startswith("'") and raw.endswith("'")
        )
        if wrapped:
            raw = raw[1:-1].strip()

        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                # Fall back to tolerant token parsing for malformed list strings.
                raw = raw[1:-1]

        tokens = [
            part.strip().strip("\"'")
            for part in re.split(r"[,;]", raw)
            if part.strip().strip("\"'")
        ]
        return tokens

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        placeholder_secret = self.jwt_secret_key.strip() in {
            "",
            "change-me-in-env",
            "replace-with-strong-random-secret",
        }
        if placeholder_secret and self.app_env in {"staging", "production"}:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a strong non-placeholder value"
            )
        if placeholder_secret and self.app_env == "development":
            warnings.warn(
                "Using placeholder JWT_SECRET_KEY in development. Set a strong secret before deployment.",
                stacklevel=1,
            )
        if not self.cors_origins:
            raise ValueError("CORS origins cannot be empty")
        return self

    @model_validator(mode="after")
    def validate_database_settings(self) -> "Settings":
        if not self.mongodb_uri.startswith("mongodb"):
            raise ValueError("MONGODB_URI must start with mongodb:// or mongodb+srv://")
        if not self.mongodb_database.strip():
            raise ValueError("MONGODB_DATABASE cannot be empty")
        if self.generation_chunk_size < 1:
            raise ValueError("generation_chunk_size must be >= 1")
        if self.generation_min_chunk_size < 1:
            raise ValueError("generation_min_chunk_size must be >= 1")
        if self.generation_target_cells_per_chunk < 1:
            raise ValueError("generation_target_cells_per_chunk must be >= 1")
        if self.async_generation_row_threshold < 1:
            raise ValueError("async_generation_row_threshold must be >= 1")
        if self.async_generation_cell_threshold < 1:
            raise ValueError("async_generation_cell_threshold must be >= 1")
        if self.quality_alert_threshold < 0:
            raise ValueError("quality_alert_threshold must be >= 0")
        return self

    @model_validator(mode="after")
    def validate_async_settings(self) -> "Settings":
        if not self.celery_broker_url and self.redis_url:
            self.celery_broker_url = self.redis_url
        if not self.celery_result_backend and self.redis_url:
            self.celery_result_backend = self.redis_url

        if self.async_generation_enabled:
            if not self.celery_broker_url:
                raise ValueError(
                    "CELERY_BROKER_URL or REDIS_URL must be configured when ASYNC_GENERATION_ENABLED=true"
                )
            if not self.celery_result_backend:
                raise ValueError(
                    "CELERY_RESULT_BACKEND or REDIS_URL must be configured when ASYNC_GENERATION_ENABLED=true"
                )
            if not (
                self.celery_broker_url.startswith("redis://")
                or self.celery_broker_url.startswith("rediss://")
            ):
                raise ValueError(
                    "CELERY_BROKER_URL must start with redis:// or rediss://"
                )
            if not (
                self.celery_result_backend.startswith("redis://")
                or self.celery_result_backend.startswith("rediss://")
            ):
                raise ValueError(
                    "CELERY_RESULT_BACKEND must start with redis:// or rediss://"
                )

        return self


settings = Settings()
