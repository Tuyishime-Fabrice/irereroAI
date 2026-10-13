from datetime import date
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "dev-only-insecure-jwt-secret-change-me-before-deploying"  # noqa: S105  # pragma: allowlist secret


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local development default only; deployments set DATABASE_URL.
    database_url: str = (
        "postgresql+psycopg://irerero:irerero@localhost:5432/irerero"  # pragma: allowlist secret
    )
    cors_origins: list[str] = ["http://localhost:3000"]

    jwt_secret: str = INSECURE_DEFAULT_SECRET
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    otp_minutes: int = 10
    otp_max_attempts: int = 5

    # Demo mode shows demo credentials and one-time codes on screen and pins the calendar to
    # the seeded weeks. It must be off anywhere real people sign in.
    demo_mode: bool = True
    demo_current_week: date = date(2026, 9, 21)
    demo_first_week: date = date(2026, 7, 6)

    catchment_minutes: int = 30
    metres_per_minute: float = 67.0

    # Phase 2: a language-model provider for the assistant. Unused in Phase 1.
    llm_api_key: str | None = None

    @model_validator(mode="after")
    def _refuse_insecure_production(self) -> "Settings":
        if not self.demo_mode and self.jwt_secret == INSECURE_DEFAULT_SECRET:
            raise ValueError("Set JWT_SECRET when DEMO_MODE is off.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
