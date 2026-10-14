from fastapi import APIRouter
from pydantic import BaseModel

from irerero_api.config import get_settings
from irerero_engine.coverage import CATCHMENT_STEPS

router = APIRouter(tags=["system"])


class AppSettings(BaseModel):
    demo_mode: bool
    catchment_minutes: int
    catchment_steps: list[int]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings", response_model=AppSettings)
def app_settings() -> AppSettings:
    settings = get_settings()
    return AppSettings(
        demo_mode=settings.demo_mode,
        catchment_minutes=settings.catchment_minutes,
        catchment_steps=list(CATCHMENT_STEPS),
    )
