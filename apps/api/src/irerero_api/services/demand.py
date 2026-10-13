"""Record unmet demand from parents. Raw coordinates are snapped before anything is stored."""

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from irerero_contract.enums import DemandKind, Origin
from irerero_contract.grid import cell_centre, cell_id, nearest_sector
from irerero_contract.tables import AdminUnit, DemandSignal


def snap(session: Session, lon: float, lat: float) -> tuple[str, str]:
    """(grid cell id, sector code) for a location. The location itself is not kept."""
    cell = session.execute(select(cell_id(lon, lat))).scalar_one()
    sector = session.execute(nearest_sector(cell_centre(lon, lat))).scalar_one()
    return cell, sector


def record_demand(
    session: Session, kind: DemandKind, lon: float, lat: float, age_band: str | None, origin: Origin
) -> tuple[str, str]:
    cell, sector = snap(session, lon, lat)
    session.execute(
        insert(DemandSignal).values(
            kind=kind,
            grid_cell=cell,
            cell_centre=cell_centre(lon, lat),
            sector_code=sector,
            age_band=age_band,
            origin=origin,
        )
    )
    name = session.scalar(select(AdminUnit.name).where(AdminUnit.code == sector)) or sector
    return cell, name
