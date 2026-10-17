"""Joining area files to admin units, and writing their values as area indicators.

Every area dataset joins on the official admin code. Until the official boundaries are loaded
the demo boundaries have no official codes, so a row may give the area's name instead; names
are matched within their level after removing case, accents and punctuation.
"""

import unicodedata
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import Connection, insert, text

from irerero_contract.indicators import INDICATORS
from irerero_contract.tables import AreaIndicator
from pipelines.sources.readers import SchemaError
from pipelines.sources.spec import Dataset

LEVELS = ("province", "district", "sector", "cell", "village")
SUFFIXES = (" province", " district", " sector", " city of kigali")


def normalise(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    for suffix in SUFFIXES:
        plain = plain.removesuffix(suffix)
    return "".join(ch for ch in plain if ch.isalnum())


class AdminResolver:
    """Maps a row's (level, official code or name) to the admin unit code used everywhere."""

    def __init__(self, conn: Connection) -> None:
        self.by_code: dict[tuple[str, str], str] = {}
        self.by_name: dict[tuple[str, str], list[str]] = defaultdict(list)
        self.parent_name: dict[str, str] = {}
        rows = conn.execute(
            text(
                "SELECT a.code, a.level, a.name, a.nisr_code, p.name AS parent FROM admin_unit a "
                "LEFT JOIN admin_unit p ON p.code = a.parent_code"
            )
        ).all()
        for row in rows:
            if row.nisr_code:
                self.by_code[(row.level, row.nisr_code)] = row.code
            self.by_name[(row.level, normalise(row.name))].append(row.code)
            self.parent_name[row.code] = normalise(row.parent or "")

    def resolve(
        self,
        level: str,
        code: str | None,
        name: str | None,
        where: str,
        parent_name: str | None = None,
    ) -> str:
        if level not in LEVELS:
            raise SchemaError(f"{where}: admin_level must be one of {', '.join(LEVELS)}")
        if code:
            found = self.by_code.get((level, code))
            if found:
                return found
            if not name:
                raise SchemaError(
                    f"{where}: no {level} has official code {code}. Load the official "
                    "boundaries first, or give admin_name as well."
                )
        if name:
            matches = self.by_name.get((level, normalise(name)), [])
            if parent_name:
                matches = [m for m in matches if self.parent_name[m] == normalise(parent_name)]
            if len(matches) == 1:
                return matches[0]
            if not matches:
                within = f" in {parent_name}" if parent_name else ""
                raise SchemaError(f"{where}: no {level} is called {name}{within}")
            raise SchemaError(
                f"{where}: more than one {level} is called {name}; give parent_name or admin_code"
            )
        raise SchemaError(f"{where}: give admin_code or admin_name")


def resolve_rows(
    conn: Connection, rows: Iterable[Mapping[str, Any]], file: str
) -> list[tuple[str, Mapping[str, Any]]]:
    resolver = AdminResolver(conn)
    out = [
        (
            resolver.resolve(
                row["admin_level"],
                row.get("admin_code"),
                row.get("admin_name"),
                f"{file} row {i}",
                row.get("parent_name"),
            ),
            row,
        )
        for i, row in enumerate(rows, start=1)
    ]
    codes = [code for code, _ in out]
    duplicates = sorted({c for c in codes if codes.count(c) > 1})
    if duplicates:
        raise SchemaError(f"{file}: more than one row for {', '.join(duplicates)}")
    return out


def write_indicators(
    conn: Connection,
    dataset: Dataset,
    reference_year: int,
    run_id: uuid.UUID,
    values: Iterable[tuple[str, str, float, float | None, float | None, int | None]],
) -> int:
    """values: (area code, indicator code, value, low, high, sample size)."""
    rows = [
        {
            "area_code": area,
            "indicator": indicator,
            "value": value,
            "low": low,
            "high": high,
            "unit": INDICATORS[indicator].unit,
            "sample_size": sample,
            "source": dataset.title,
            "reference_year": reference_year,
            "origin": dataset.origin,
            "pipeline_run_id": run_id,
        }
        for area, indicator, value, low, high, sample in values
    ]
    if rows:
        conn.execute(insert(AreaIndicator), rows)
    return len(rows)


def share(part: float | None, whole: float | None) -> float | None:
    return part / whole if part is not None and whole else None
