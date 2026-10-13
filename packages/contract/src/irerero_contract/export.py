"""Export the contract: JSON Schemas for loadable datasets and the field reference.

python -m irerero_contract.export          # write data/contract/*.json and the docs section
python -m irerero_contract.export --check  # fail if either is out of date (used in CI)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    Integer,
    SmallInteger,
    String,
    Table,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

import irerero_contract.tables  # noqa: F401
from irerero_contract.base import Base
from irerero_contract.indicators import INDICATORS

# Datasets a pipeline loads from files. Account and audit tables are app-internal.
LOADABLE = (
    "admin_unit",
    "area_indicator",
    "candidate_site",
    "centre",
    "coverage_snapshot",
    "data_source",
    "model_version",
    "need_estimate",
    "pipeline_run",
    "unit_cost",
    "weekly_report",
)

# Rwanda's bounding box, so a file with swapped or projected coordinates fails validation.
LON_RANGE = (28.8, 31.0)
LAT_RANGE = (-2.9, -1.0)
POSITION = {
    "type": "array",
    "prefixItems": [
        {"type": "number", "minimum": LON_RANGE[0], "maximum": LON_RANGE[1]},
        {"type": "number", "minimum": LAT_RANGE[0], "maximum": LAT_RANGE[1]},
    ],
    "minItems": 2,
    "maxItems": 2,
}
GEOJSON = {
    "POINT": {
        "type": "object",
        "required": ["type", "coordinates"],
        "properties": {"type": {"const": "Point"}, "coordinates": POSITION},
    },
    "MULTIPOLYGON": {
        "type": "object",
        "required": ["type", "coordinates"],
        "properties": {
            "type": {"const": "MultiPolygon"},
            "coordinates": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "array", "items": POSITION}},
            },
        },
    },
}

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "data" / "contract"
DOC_PATH = REPO_ROOT / "docs" / "DATA_CONTRACT.md"
BEGIN = "<!-- BEGIN GENERATED FIELD REFERENCE -->"
END = "<!-- END GENERATED FIELD REFERENCE -->"


def _column_schema(column: Column[Any]) -> dict[str, Any]:
    kind = column.type
    schema: dict[str, Any]
    if isinstance(kind, Enum):
        schema = {"type": "string", "enum": list(kind.enums)}
    elif isinstance(kind, Geometry):
        schema = dict(GEOJSON[str(kind.geometry_type)])
    elif isinstance(kind, Uuid):
        schema = {"type": "string", "format": "uuid"}
    elif isinstance(kind, DateTime):
        schema = {"type": "string", "format": "date-time"}
    elif isinstance(kind, Date):
        schema = {"type": "string", "format": "date"}
    elif isinstance(kind, Boolean):
        schema = {"type": "boolean"}
    elif isinstance(kind, Integer | SmallInteger | BigInteger):
        schema = {"type": "integer"}
    elif isinstance(kind, Float):
        schema = {"type": "number"}
    elif isinstance(kind, ARRAY):
        items_enum = column.info.get("items_enum")
        items = {"type": "string", "enum": [m.value for m in items_enum]} if items_enum else {}
        schema = {"type": "array", "items": items}
    elif isinstance(kind, JSONB):
        schema = {}
        if "items" in column.info:
            schema = {"type": "array", "items": column.info["items"]}
        elif "additionalProperties" in column.info:
            schema = {"type": "object", "additionalProperties": column.info["additionalProperties"]}
    elif isinstance(kind, String | Text):
        schema = {"type": "string"}
        if isinstance(kind, String) and kind.length:
            schema["maxLength"] = kind.length
    else:
        raise TypeError(f"No JSON Schema mapping for {column.table.name}.{column.name}: {kind!r}")
    for key in ("minimum", "maximum"):
        if key in column.info:
            schema[key] = column.info[key]
    if column.nullable and not column.primary_key:
        schema = {"anyOf": [schema, {"type": "null"}]}
    schema["description"] = column.comment or ""
    return schema


def _is_required(column: Column[Any]) -> bool:
    has_default = column.default is not None or column.server_default is not None
    return not column.nullable and not has_default


def _table_doc(table: Table) -> str:
    for mapper in Base.registry.mappers:
        if mapper.local_table is table:
            return " ".join((mapper.class_.__doc__ or "").split())
    return ""


def table_schema(table: Table) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://irereroai.rw/contract/{table.name}.schema.json",
        "title": table.name,
        "description": _table_doc(table),
        "type": "object",
        "additionalProperties": False,
        "required": [c.name for c in table.columns if _is_required(c)],
        "properties": {c.name: _column_schema(c) for c in table.columns},
    }


def _type_label(column: Column[Any]) -> str:
    kind = column.type
    if isinstance(kind, Enum):
        return "code"
    if isinstance(kind, Geometry):
        return f"{str(kind.geometry_type).lower()} 4326"
    if isinstance(kind, JSONB):
        return "json"
    if isinstance(kind, ARRAY):
        return "list"
    return type(kind).__name__.lower()


def field_reference() -> str:
    lines = [
        BEGIN,
        "",
        "### Indicator codes",
        "",
        "| Code | Unit | Meaning |",
        "| --- | --- | --- |",
    ]
    lines += [f"| `{i.code}` | {i.unit} | {i.description} |" for i in INDICATORS.values()]
    lines.append("")
    for name in sorted(Base.metadata.tables):
        table = Base.metadata.tables[name]
        lines += [f"### `{name}`", "", _table_doc(table), ""]
        if name in LOADABLE:
            lines += [
                f"JSON Schema: [`data/contract/{name}.schema.json`]"
                f"(../data/contract/{name}.schema.json)",
                "",
            ]
        lines += ["| Field | Type | Required | Description |", "| --- | --- | --- | --- |"]
        for column in table.columns:
            required = "key" if column.primary_key else ("yes" if not column.nullable else "")
            comment = (column.comment or "").replace("|", "\\|")
            lines.append(f"| `{column.name}` | {_type_label(column)} | {required} | {comment} |")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def expected_files() -> dict[Path, str]:
    files = {
        SCHEMA_DIR / f"{name}.schema.json": json.dumps(
            table_schema(Base.metadata.tables[name]), indent=2, ensure_ascii=False
        )
        + "\n"
        for name in LOADABLE
    }
    doc = DOC_PATH.read_text(encoding="utf-8")
    start, end = doc.index(BEGIN), doc.index(END) + len(END)
    files[DOC_PATH] = doc[:start] + field_reference() + doc[end:]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when outputs are stale")
    args = parser.parse_args()
    stale = []
    for path, content in expected_files().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            stale.append(path)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    if args.check and stale:
        for path in stale:
            print(f"out of date: {path.relative_to(REPO_ROOT)}", file=sys.stderr)
        print("run: uv run python -m irerero_contract.export", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
