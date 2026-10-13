from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from irerero_api.calendar import current_week, weeks_until
from irerero_api.config import get_settings

router = APIRouter(tags=["system"])


class Calendar(BaseModel):
    current_week: date
    weeks: list[date]
    demo_mode: bool


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/calendar", response_model=Calendar)
def calendar() -> Calendar:
    settings = get_settings()
    return Calendar(
        current_week=current_week(settings),
        weeks=weeks_until(settings),
        demo_mode=settings.demo_mode,
    )
