"""Area tables: one row per area (admin level plus code or name), values become indicators."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from sqlalchemy import Connection

from pipelines.runs import CheckResult
from pipelines.sources.areas import resolve_rows, share, write_indicators
from pipelines.sources.base import Loader, LoadReport
from pipelines.sources.readers import interval, read_csv


@dataclass(frozen=True)
class Direct:
    """An indicator read straight from a column, with its _low/_high interval if given."""

    indicator: str
    column: str


@dataclass(frozen=True)
class Ratio:
    """An indicator computed as one count column over another."""

    indicator: str
    part: str
    whole: str


class AreaTableLoader(Loader):
    values: ClassVar[Sequence[Direct | Ratio]]

    def load(self, conn: Connection, folder: Path, run_id: uuid.UUID) -> LoadReport:
        file = self.dataset.files[0].name
        rows = read_csv(folder / file, self.dataset.columns)
        resolved = resolve_rows(conn, rows, file)
        values = []
        for i, (area, row) in enumerate(resolved, start=1):
            sample = row.get("sample_size")
            for spec in self.values:
                if isinstance(spec, Direct):
                    found = interval(row, spec.column, f"{file} row {i}")
                    if found is not None:
                        values.append((area, spec.indicator, *found, sample))
                else:
                    ratio = share(row.get(spec.part), row.get(spec.whole))
                    if ratio is not None:
                        values.append((area, spec.indicator, ratio, None, None, None))
        year = self.dataset.reference_year or 0
        written = write_indicators(conn, self.dataset, year, run_id, values)
        levels = sorted({row["admin_level"] for _, row in resolved})
        return LoadReport(
            {"area_indicator": written},
            [
                CheckResult("areas_matched", True, f"{len(resolved)} areas ({', '.join(levels)})"),
                CheckResult("values_written", written > 0, f"{written} indicator values"),
            ],
        )
