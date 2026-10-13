from typing import Any

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, Provenance, enum_type, multipolygon, point
from irerero_contract.enums import AdminLevel


class AdminUnit(Provenance, Base):
    """Administrative areas from country down to village, with geometry simplified per zoom."""

    __tablename__ = "admin_unit"

    code: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Stable IrereroAI code, e.g. D-GICUMBI or S-GICUMBI-BYUMBA. All tables join on it",
    )
    name: Mapped[str] = mapped_column(String(120), comment="Official name as published")
    level: Mapped[AdminLevel] = mapped_column(
        enum_type(AdminLevel),
        index=True,
        comment="country | province | district | sector | cell | village",
    )
    parent_code: Mapped[str | None] = mapped_column(
        ForeignKey("admin_unit.code"), index=True, comment="Code of the enclosing unit"
    )
    nisr_code: Mapped[str | None] = mapped_column(
        String(16),
        unique=True,
        comment="Official NISR administrative code. Filled by the Phase 2 boundaries adapter",
    )
    source_ref: Mapped[str | None] = mapped_column(
        String(64), comment="Identifier in the boundary source, e.g. the geoBoundaries shapeID"
    )
    geom: Mapped[Any] = mapped_column(multipolygon(), comment="Boundary, EPSG:4326, full detail")
    geom_medium: Mapped[Any] = mapped_column(
        multipolygon(), comment="Boundary simplified for district zoom (about 50 m tolerance)"
    )
    geom_coarse: Mapped[Any] = mapped_column(
        multipolygon(), comment="Boundary simplified for national zoom (about 500 m tolerance)"
    )
    centroid: Mapped[Any] = mapped_column(point(), comment="Point on surface, EPSG:4326")
    area_km2: Mapped[float] = mapped_column(
        Float, comment="Area computed in EPSG:32735 (UTM 35S)", info={"minimum": 0}
    )
