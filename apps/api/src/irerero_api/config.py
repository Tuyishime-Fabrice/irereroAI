from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local development default only; deployments set DATABASE_URL.
    database_url: str = (
        "postgresql+psycopg://irerero:irerero@localhost:5432/irerero"  # pragma: allowlist secret
    )
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
