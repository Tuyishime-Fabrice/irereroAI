"""Which areas a planner may plan for.

Every planner reads the national overview at district level. Sector detail, plans and decisions
are limited to the planner's own district. Hiding things in the web app is a convenience; this is
the guard.
"""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from irerero_api.auth.principal import Principal
from irerero_contract.tables import AdminUnit


def forbidden(detail: str = "Outside your district") -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail)


@dataclass(frozen=True)
class AreaChain:
    """An area resolved to its sector, district and province codes."""

    sector: str | None
    district: str | None
    province: str | None


def resolve(session: Session, area: str) -> AreaChain:
    chain: dict[str, str] = {}
    current: str | None = area
    while current is not None:
        unit = session.get(AdminUnit, current)
        if unit is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown area {area}")
        chain[unit.level.value] = unit.code
        current = unit.parent_code
    return AreaChain(chain.get("sector"), chain.get("district"), chain.get("province"))


def require_district(session: Session, principal: Principal, area: str) -> AreaChain:
    """The area must be the planner's district or a sector inside it."""
    chain = resolve(session, area)
    if chain.district is None or chain.district != principal.district_code:
        raise forbidden()
    return chain
