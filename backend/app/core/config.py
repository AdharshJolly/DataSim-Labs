from pathlib import Path
from typing import Literal
import warnings

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    artifacts_dir: str = "artifacts"
    generation_chunk_size: int = 100000
    artifact_retention_hours: int = 24
    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

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
        return self


settings = Settings()
