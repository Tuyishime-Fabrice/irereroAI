"""Read a dataset's file and check it against its declared columns, with clear messages."""

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pipelines.sources.spec import Column

TRUE = {"1", "true", "yes", "y"}
FALSE = {"0", "false", "no", "n"}


class SchemaError(ValueError):
    """A file does not match its dataset's declared columns. The message says how to fix it."""


@dataclass(frozen=True)
class Feature:
    properties: dict[str, Any]
    geometry: dict[str, Any]


def _convert(column: Column, raw: object, where: str) -> object:
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        if column.required:
            raise SchemaError(f"{where}: {column.name} is required")
        return None
    text = str(raw).strip()
    try:
        if column.type == "text":
            return text
        if column.type == "integer":
            value = int(float(text))
            if value < 0:
                raise SchemaError(f"{where}: {column.name} cannot be negative")
            return value
        if column.type in ("number", "share"):
            number = float(text)
            if column.type == "share" and not 0 <= number <= 1:
                raise SchemaError(f"{where}: {column.name} must be a share between 0 and 1")
            return number
        if column.type == "date":
            return date.fromisoformat(text)
        lowered = text.lower()
        if lowered in TRUE:
            return True
        if lowered in FALSE:
            return False
        raise SchemaError(f"{where}: {column.name} must be yes or no")
    except ValueError as error:
        if isinstance(error, SchemaError):
            raise
        raise SchemaError(f"{where}: {column.name} is not a valid {column.type}") from error


def _check_header(found: Sequence[str], columns: Sequence[Column], path: Path) -> None:
    missing = [c.name for c in columns if c.required and c.name not in found]
    if missing:
        raise SchemaError(f"{path.name}: missing column(s) {', '.join(missing)}")


def read_csv(path: Path, columns: Sequence[Column]) -> list[dict[str, Any]]:
    """Rows as dicts holding the declared columns only, converted to their types."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        _check_header(reader.fieldnames or [], columns, path)
        rows = [
            {c.name: _convert(c, raw.get(c.name), f"{path.name} line {i}") for c in columns}
            for i, raw in enumerate(reader, start=2)
        ]
    if not rows:
        raise SchemaError(f"{path.name}: the file has no rows")
    return rows


def read_geojson(path: Path, columns: Sequence[Column]) -> list[Feature]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection":
        raise SchemaError(f"{path.name}: expected a GeoJSON FeatureCollection")
    features = data.get("features") or []
    if not features:
        raise SchemaError(f"{path.name}: the file has no features")
    _check_header(list(features[0].get("properties") or {}), columns, path)
    out = []
    for i, feature in enumerate(features, start=1):
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        if not geometry:
            raise SchemaError(f"{path.name} feature {i}: has no geometry")
        out.append(
            Feature(
                {
                    c.name: _convert(c, props.get(c.name), f"{path.name} feature {i}")
                    for c in columns
                },
                geometry,
            )
        )
    return out


def interval(
    row: dict[str, Any], name: str, where: str
) -> tuple[float, float | None, float | None] | None:
    """(estimate, low, high) from columns name, name_low and name_high; None when empty."""
    value, low, high = row.get(name), row.get(f"{name}_low"), row.get(f"{name}_high")
    if value is None:
        return None
    if (low is None) != (high is None):
        raise SchemaError(f"{where}: give both {name}_low and {name}_high, or neither")
    if low is not None and high is not None and not low <= value <= high:
        raise SchemaError(f"{where}: {name}_low <= {name} <= {name}_high does not hold")
    return value, low, high
