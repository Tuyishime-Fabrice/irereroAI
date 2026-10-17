"""The shape every dataset loader shares."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from sqlalchemy import Connection

from pipelines.runs import CheckResult
from pipelines.sources.spec import Column, Dataset


@dataclass
class LoadReport:
    rows: dict[str, int] = field(default_factory=dict)
    checks: list[CheckResult] = field(default_factory=list)


class Loader(ABC):
    dataset: ClassVar[Dataset]

    def folder(self, raw: Path) -> Path:
        return raw / self.dataset.key

    def present(self, raw: Path) -> bool:
        return self.dataset.present(raw)

    @abstractmethod
    def load(self, conn: Connection, folder: Path, run_id: uuid.UUID) -> LoadReport:
        """Validate the files and write them. Raise SchemaError with a clear message if wrong."""


def interval_columns(name: str, description: str, *, required: bool = True) -> tuple[Column, ...]:
    return (
        Column(name, "share", description, required=required),
        Column(f"{name}_low", "share", "Lower bound of the 95% interval", required=False),
        Column(f"{name}_high", "share", "Upper bound of the 95% interval", required=False),
    )
