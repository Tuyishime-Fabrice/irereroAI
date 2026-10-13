import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, created_at_column, enum_type, new_uuid, point
from irerero_contract.enums import DemandKind, Origin


class DemandSignal(Base):
    """A parent search with no result, or a request for a centre.

    The raw parent location is never stored: the API snaps it to a 500 m grid cell in
    EPSG:32735 before anything is written.
    """

    __tablename__ = "demand_signal"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Id")
    kind: Mapped[DemandKind] = mapped_column(
        enum_type(DemandKind), comment="empty_search | centre_request"
    )
    grid_cell: Mapped[str] = mapped_column(
        String(32), index=True, comment="500 m cell id in EPSG:32735: 'E{easting}N{northing}'"
    )
    cell_centre: Mapped[Any] = mapped_column(point(), comment="Centre of the cell, EPSG:4326")
    sector_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="Sector containing the cell centre"
    )
    age_band: Mapped[str | None] = mapped_column(
        String(8), comment="Age band searched for: 0_2 | 3_6"
    )
    origin: Mapped[Origin] = mapped_column(enum_type(Origin), comment="Origin of the signal")
    created_at: Mapped[datetime] = created_at_column()
