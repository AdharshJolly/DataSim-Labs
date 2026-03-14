from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "DataSim Lab API"
    api_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql://postgres:6ionwHwUT1JF7XaH@db.nzlznwmbtelgjnktddvp.supabase.co:5432/postgres?sslmode=require"
    )

    redis_url: str = "redis://localhost:6379/0"
    artifacts_dir: str = "artifacts"
    generation_chunk_size: int = 100000

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
