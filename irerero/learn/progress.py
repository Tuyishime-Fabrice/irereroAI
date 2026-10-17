"""Aggregates of course progress. Never individual scores outside the caregiver's own view."""

from sqlalchemy import Engine


def completion_by_district(eng: Engine) -> dict[str, float]:
    """Share of required assignments completed, per district. Filled in with LEARN."""
    return {}
