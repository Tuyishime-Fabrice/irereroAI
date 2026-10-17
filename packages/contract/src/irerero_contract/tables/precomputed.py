"""Tables the build precomputes so the planner's map and optimizer answer instantly."""

from typing import Any

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, Provenance, enum_type, point
from irerero_contract.enums import FacilityKind, TravelMethod


class PopulationCell(Provenance, Base):
    """Where children live inside a sector: 500 m cells, each with its share of the sector.

    From WorldPop when loaded, otherwise an even spread by area.
    """

    __tablename__ = "population_cell"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="'{sector}:{cell}', cell on the 500 m grid"
    )
    sector_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="Sector the cell belongs to"
    )
    location: Mapped[Any] = mapped_column(point(), comment="Cell point, EPSG:4326")
    share: Mapped[float] = mapped_column(
        Float,
        comment="Share of the sector's children living in the cell",
        info={"minimum": 0, "maximum": 1},
    )


class Catchment(Base):
    """Walking minutes from a centre or candidate site to each population cell it can reach."""

    __tablename__ = "catchment"

    seat_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, comment="Centre code or candidate site code"
    )
    cell_id: Mapped[str] = mapped_column(
        ForeignKey("population_cell.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Population cell",
    )
    walk_minutes: Mapped[float] = mapped_column(
        Float, comment="Estimated walking time in minutes", info={"minimum": 0}
    )
    method: Mapped[TravelMethod] = mapped_column(
        enum_type(TravelMethod), comment="road_network | straight_line"
    )


class Facility(Provenance, Base):
    """Schools, childcare and health facilities, shown on the planner's map."""

    __tablename__ = "facility"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="Source id")
    kind: Mapped[FacilityKind] = mapped_column(
        enum_type(FacilityKind), comment="school | childcare | health"
    )
    name: Mapped[str | None] = mapped_column(String(160), comment="Name, when the source has one")
    sector_code: Mapped[str] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="Sector containing the facility"
    )
    location: Mapped[Any] = mapped_column(point(), comment="Facility location, EPSG:4326")
