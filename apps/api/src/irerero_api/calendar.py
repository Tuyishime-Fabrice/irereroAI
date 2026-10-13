"""The reporting calendar: Monday-starting weeks, pinned to the seeded weeks in demo mode."""

from datetime import date, timedelta

from irerero_api.config import Settings

WEEKS_SHOWN = 12


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def current_week(settings: Settings) -> date:
    return settings.demo_current_week if settings.demo_mode else monday(date.today())  # noqa: DTZ011


def weeks_until(settings: Settings, as_of: date | None = None) -> list[date]:
    """Reporting weeks from the first shown week up to `as_of` (default: the current week)."""
    end = monday(as_of) if as_of else current_week(settings)
    start = (
        settings.demo_first_week if settings.demo_mode else end - timedelta(weeks=WEEKS_SHOWN - 1)
    )
    weeks = []
    week = start
    while week <= end:
        weeks.append(week)
        week += timedelta(weeks=1)
    return weeks
