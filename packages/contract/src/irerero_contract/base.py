"""Declarative base, shared column helpers and the provenance mixin.

Column comments are the field documentation: they are written to Postgres, exported to the
JSON Schemas in data/contract/ and rendered into docs/DATA_CONTRACT.md.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, MetaData, SmallInteger, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from irerero_contract.enums import Origin

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Storage CRS. Areas and distances are computed in UTM zone 35S (EPSG:32735).
SRID = 4326
METRIC_SRID = 32735


# JSON Schema for the drivers list shared by need estimates and recommendations.
DRIVERS_INFO: dict[str, Any] = {
    "items": {
        "type": "object",
        "required": ["feature", "label_en", "label_rw", "contribution"],
        "properties": {
            "feature": {"type": "string"},
            "label_en": {"type": "string"},
            "label_rw": {"type": "string"},
            "contribution": {"type": "number"},
        },
    }
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def enum_type(enum_cls: type[StrEnum]) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [member.value for member in members],
        name=enum_cls.__name__.lower(),
        validate_strings=True,
    )


def point() -> Geometry:
    return Geometry("POINT", srid=SRID, spatial_index=True)


def multipolygon() -> Geometry:
    return Geometry("MULTIPOLYGON", srid=SRID, spatial_index=True)


def count(comment: str, *, nullable: bool = False, maximum: int | None = None) -> Mapped[Any]:
    """A non-negative count. Range checks live in table CHECK constraints."""
    info: dict[str, Any] = {"minimum": 0}
    if maximum is not None:
        info["maximum"] = maximum
    return mapped_column(Integer, nullable=nullable, comment=comment, info=info)


def days(comment: str) -> Mapped[int]:
    return mapped_column(SmallInteger, comment=comment, info={"minimum": 0, "maximum": 6})


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def created_at_column() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="When the row was written"
    )


class Provenance:
    """Every statistical or reported record says where it came from."""

    source: Mapped[str] = mapped_column(
        String(160),
        comment='Named source, for example "NISR Census 2022" or "IrereroAI demo generator"',
    )
    reference_year: Mapped[int] = mapped_column(
        SmallInteger,
        comment="Year the values describe, not the year they were loaded",
        info={"minimum": 2000, "maximum": 2100},
    )
    origin: Mapped[Origin] = mapped_column(
        enum_type(Origin), comment="official | public | partner | simulated. Drives UI badges"
    )

    @declared_attr
    def pipeline_run_id(cls) -> Mapped[uuid.UUID | None]:  # noqa: N805
        return mapped_column(
            ForeignKey("pipeline_run.id"),
            nullable=True,
            index=True,
            comment="Pipeline run that loaded the row. Null for records entered through the app",
        )
