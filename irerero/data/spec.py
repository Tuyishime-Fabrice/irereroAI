"""What each dataset must look like. One declaration drives validation and DATA_SOURCES.md."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ColumnType = Literal[
    "text", "integer", "number", "share", "boolean", "date", "longitude", "latitude"
]

# Rwanda with a small margin: a coordinate outside this box is a typo or swapped lon/lat.
COORDINATE_RANGE = {"longitude": (28.7, 31.0), "latitude": (-2.95, -1.0)}


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType
    description: str
    required: bool = True


@dataclass(frozen=True)
class Dataset:
    key: str
    """Folder under data/raw/ and the source_id of everything it produces."""
    title: str
    publisher: str
    files: tuple[str, ...]
    """File names (or glob patterns) expected in data/raw/<key>/."""
    format: str
    columns: tuple[Column, ...]
    level: str
    reference_period: str
    licence: str
    url: str | None
    used_by: tuple[str, ...]
    status: str
    """Status of its values when the real file is loaded."""
    fallback: str
    """What stands in, labelled simulated, while the file is missing."""
    notes: tuple[str, ...] = field(default=())

    def folder(self, raw: Path) -> Path:
        return raw / self.key

    def present(self, raw: Path) -> bool:
        folder = self.folder(raw)
        return all(any(folder.glob(pattern)) for pattern in self.files)


NAME_COLUMNS = (
    Column("sector_name", "text", "Sector name as printed in the source"),
    Column("district_name", "text", "District name as printed in the source"),
)
DISTRICT_COLUMN = (Column("district_name", "text", "District name as printed in the source"),)
PAGE_COLUMN = Column("source_page", "text", "Page or table the value was read from", required=False)
