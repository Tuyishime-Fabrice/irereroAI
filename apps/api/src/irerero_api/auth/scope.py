"""Which areas and centres a principal may read or act on.

Every scoped endpoint calls one of these checks; hiding things in the web app is a convenience,
this is the guard.
"""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from irerero_api.auth.principal import Principal
from irerero_contract.enums import ScopeLevel
from irerero_contract.tables import AdminUnit, Centre


def forbidden(detail: str = "Outside your scope") -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail)


@dataclass(frozen=True)
class AreaChain:
    """An area or centre resolved to its sector, district and province codes."""

    centre: str | None
    sector: str | None
    district: str | None
    province: str | None


def _chain_from_area(session: Session, code: str) -> AreaChain:
    chain: dict[str, str] = {}
    current: str | None = code
    while current is not None:
        unit = session.get(AdminUnit, current)
        if unit is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown area {code}")
        chain[unit.level.value] = unit.code
        current = unit.parent_code
    return AreaChain(None, chain.get("sector"), chain.get("district"), chain.get("province"))


def resolve(session: Session, *, area: str | None = None, centre: str | None = None) -> AreaChain:
    if centre is not None:
        sector = session.scalar(select(Centre.sector_code).where(Centre.code == centre))
        if sector is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown centre {centre}")
        chain = _chain_from_area(session, sector)
        return AreaChain(centre, chain.sector, chain.district, chain.province)
    if area is None:
        raise ValueError("resolve needs an area or a centre")
    return _chain_from_area(session, area)


def allows(principal: Principal, chain: AreaChain) -> bool:
    level, code = principal.scope_level, principal.scope_code
    if level is ScopeLevel.NATIONAL:
        return True
    if level is ScopeLevel.DISTRICT:
        return chain.district == code
    if level is ScopeLevel.SECTOR:
        return chain.sector == code
    if level is ScopeLevel.CENTRE:
        return chain.centre == code
    return False


def require_area(session: Session, principal: Principal, area: str) -> AreaChain:
    chain = resolve(session, area=area)
    if not allows(principal, chain):
        raise forbidden()
    return chain


def require_centre(session: Session, principal: Principal, centre: str) -> AreaChain:
    chain = resolve(session, centre=centre)
    if not allows(principal, chain):
        raise forbidden()
    return chain


def default_area(principal: Principal) -> str:
    """The area a principal works in, used when an endpoint is called without one."""
    if principal.scope_level is ScopeLevel.NATIONAL or principal.scope_code is None:
        return "RW"
    return principal.scope_code
