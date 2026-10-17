"""What a dataset must look like, declared once and used for validation and DATA_SOURCES.md."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from irerero_contract.enums import Origin

ColumnType = Literal["text", "integer", "number", "share", "date", "boolean"]
FileFormat = Literal["csv", "geojson", "geotiff", "osm.pbf"]
Level = Literal[
    "province", "district", "sector", "cell", "village", "point", "raster", "road network"
]


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType
    description: str
    required: bool = True


@dataclass(frozen=True)
class ExpectedFile:
    name: str
    format: FileFormat
    description: str
    required: bool = True


# Area files identify each row by its official code or, until the official boundaries are
# loaded, by its name. Either one is enough; the code wins when both are given.
ADMIN_COLUMNS = (
    Column("admin_level", "text", "province | district | sector | cell | village of the row"),
    Column("admin_code", "text", "Official NISR code of the area", required=False),
    Column(
        "admin_name",
        "text",
        "Area name as published; used when admin_code is empty",
        required=False,
    ),
    Column(
        "parent_name",
        "text",
        "Name of the area one level up, when admin_name is shared (sector names repeat "
        "across districts)",
        required=False,
    ),
)
INTERVAL_NOTE = (
    "Columns ending in _low and _high are the 95% interval. Leave them empty when the source "
    "publishes none; the loader then records the value without an interval."
)


@dataclass(frozen=True)
class Dataset:
    key: str
    """Folder under data/raw/ and the dataset's id everywhere else."""
    title: str
    publisher: str
    access: str
    """How to get it: open download, free registration, or agreement."""
    url: str | None
    licence: str
    origin: Origin
    reference_year: int | None
    """Year the data describe; None for living sources such as OpenStreetMap."""
    files: tuple[ExpectedFile, ...]
    columns: tuple[Column, ...]
    level: Level
    joins_on: str
    used_by: tuple[str, ...]
    produces: tuple[str, ...]
    """Tables, and area_indicator codes, the loader writes."""
    fallback: str
    """What stands in while the file is missing."""
    notes: tuple[str, ...] = field(default=())
    optional: bool = False

    def present(self, raw: Path) -> bool:
        """True when every required file is in data/raw/<key>/."""
        return all((raw / self.key / f.name).is_file() for f in self.files if f.required)
