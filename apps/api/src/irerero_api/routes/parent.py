"""Parents: saved searches and self-service deletion. Locations are stored as grid cells only."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.db import get_session
from irerero_contract.enums import Role
from irerero_contract.grid import cell_centre, cell_id
from irerero_contract.tables import OtpChallenge, SavedSearch, UserAccount

router = APIRouter(prefix="/parent", tags=["parent"])
SessionDep = Annotated[Session, Depends(get_session)]
ParentDep = Annotated[Principal, Depends(require_roles(Role.PARENT))]


class SavedSearchIn(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    lon: float = Field(ge=28.8, le=31.0)
    lat: float = Field(ge=-2.9, le=-1.0)
    filters: dict[str, Any] = Field(default_factory=dict)


class SavedSearchOut(BaseModel):
    id: uuid.UUID
    label: str
    lon: float
    lat: float
    filters: dict[str, Any]


@router.get("/searches", response_model=list[SavedSearchOut])
def list_searches(session: SessionDep, principal: ParentDep) -> list[SavedSearchOut]:
    rows = session.execute(
        select(
            SavedSearch.id,
            SavedSearch.label,
            func.ST_X(SavedSearch.cell_centre).label("lon"),
            func.ST_Y(SavedSearch.cell_centre).label("lat"),
            SavedSearch.filters,
        )
        .where(SavedSearch.user_id == principal.id)
        .order_by(SavedSearch.created_at)
    ).all()
    return [SavedSearchOut.model_validate(r._mapping) for r in rows]


@router.post("/searches", response_model=SavedSearchOut, status_code=status.HTTP_201_CREATED)
def save_search(body: SavedSearchIn, session: SessionDep, principal: ParentDep) -> SavedSearchOut:
    search = SavedSearch(
        user_id=principal.id,
        label=body.label,
        grid_cell=session.execute(select(cell_id(body.lon, body.lat))).scalar_one(),
        cell_centre=cell_centre(body.lon, body.lat),
        filters=body.filters,
    )
    session.add(search)
    session.flush()
    lon, lat = session.execute(
        select(func.ST_X(SavedSearch.cell_centre), func.ST_Y(SavedSearch.cell_centre)).where(
            SavedSearch.id == search.id
        )
    ).one()
    return SavedSearchOut(id=search.id, label=search.label, lon=lon, lat=lat, filters=body.filters)


@router.delete("/searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_search(search_id: uuid.UUID, session: SessionDep, principal: ParentDep) -> None:
    result = session.execute(
        delete(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == principal.id)
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such saved search")


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(session: SessionDep, principal: ParentDep) -> None:
    """Deletes the parent's phone number and saved searches. Demand signals were never linked."""
    phone = session.scalar(select(UserAccount.phone).where(UserAccount.id == principal.id))
    session.execute(delete(OtpChallenge).where(OtpChallenge.phone == phone))
    session.execute(delete(UserAccount).where(UserAccount.id == principal.id))
