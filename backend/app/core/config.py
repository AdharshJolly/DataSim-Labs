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
        extra="ignore",
    )

    app_name: str = "DataSim Lab API"
    api_prefix: str = "/api/v1"
    app_env: Literal["development", "staging", "production"] = "development"

    database_url: str
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    redis_url: str = "redis://localhost:6379/0"
    artifacts_dir: str = "artifacts"
    generation_chunk_size: int = 100000
    artifact_retention_hours: int = 24
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    auth_cookie_name: str = "datasim_access_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

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

    @property
    def sqlalchemy_database_url(self) -> str:
        if (
            self.database_url.startswith("postgresql://")
            and "+psycopg" not in self.database_url
        ):
            return self.database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        return self.database_url


settings = Settings()
