"""Write DATA_SOURCES.md from the dataset declarations.

python -m irerero.data            # create data/raw/<dataset>/ folders and list what is present
python -m irerero.data --write    # regenerate DATA_SOURCES.md
python -m irerero.data --check    # fail if DATA_SOURCES.md is out of date
"""

import argparse
import sys

from irerero.config import RAW, ROOT
from irerero.data.registry import DATASETS
from irerero.data.spec import Dataset

DOC = ROOT / "DATA_SOURCES.md"
TYPES = {
    "text": "text",
    "integer": "whole number ≥ 0",
    "number": "number",
    "share": "share, 0 to 1",
    "boolean": "yes / no",
    "date": "YYYY-MM-DD",
    "longitude": "longitude, WGS84 (28.7 to 31.0)",
    "latitude": "latitude, WGS84 (-2.95 to -1.0)",
}


def _section(i: int, d: Dataset) -> list[str]:
    lines = [
        "",
        f'<a id="{d.key}"></a>',
        "",
        f"## {i}. {d.title}",
        "",
        f"| | |\n| --- | --- |\n| Publisher | {d.publisher} |",
        f"| Folder | `data/raw/{d.key}/` |" if d.files else "| Folder | none |",
        f"| Expected files | {', '.join(f'`{f}`' for f in d.files) or 'none'} |",
        f"| Format | {d.format} |",
        f"| Geographic level | {d.level} |",
        f"| Reference period | {d.reference_period} |",
        f"| Licence | {d.licence} |",
        f"| Where to get it | {d.url or 'not public'} |",
        f"| Status when loaded | {d.status} |",
        f"| Used by | {'; '.join(d.used_by)} |",
        f"| While missing | {d.fallback} |",
    ]
    if d.columns:
        lines += ["", "| Column | Type | Required | Meaning |", "| --- | --- | --- | --- |"]
        lines += [
            f"| `{c.name}` | {TYPES[c.type]} | {'yes' if c.required else 'no'} | {c.description} |"
            for c in d.columns
        ]
    lines += [f"\n{note}" for note in d.notes]
    return lines


def document() -> str:
    lines = [
        "# Data sources",
        "",
        "Generated from the declarations in `irerero/data/` by `python -m irerero.data --write`;"
        " do not edit by hand.",
        "",
        "Put each file in its folder under `data/raw/` and run `make data`. Raw files never "
        "enter git. When a file is missing, the committed demo bundle in `data/demo/` stands in "
        "and every value from it carries the red SIMULATED badge and is left out of exports. "
        "When a file is present but does not match its columns, `make data` stops and names "
        "the file, line and column to fix.",
        "",
        "Every name joins to the NISR sector code through the reviewed crosswalks "
        "`data/reference/sector_name_crosswalk.csv` and `district_name_crosswalk.csv`. There is "
        "no fuzzy matching at run time: if a source spells a sector differently, add a row for "
        "that source to the crosswalk.",
        "",
        "```",
        "data/",
        "  raw/            your files, one folder per dataset (gitignored)",
        "  interim/        parsed intermediates, e.g. census tables from the PDFs (gitignored)",
        "  processed/      Parquet and simplified GeoJSON written by make data (gitignored)",
        "  reference/      reviewed crosswalks (committed)",
        "  demo/           simulated stand-ins and geoBoundaries shapes (committed)",
        "```",
        "",
        "| # | Dataset | Level | Period | Used by |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {i} | [{d.title}](#{d.key}) | {d.level} | {d.reference_period} | "
        f"{'; '.join(d.used_by)} |"
        for i, d in enumerate(DATASETS, start=1)
    ]
    for i, d in enumerate(DATASETS, start=1):
        lines += _section(i, d)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        DOC.write_text(document())
    elif args.check:
        if not DOC.exists() or DOC.read_text() != document():
            sys.exit("DATA_SOURCES.md is stale: run python -m irerero.data --write")
    else:
        for d in DATASETS:
            if d.files:
                d.folder(RAW).mkdir(parents=True, exist_ok=True)
                print(f"{d.key:16} {'present' if d.present(RAW) else 'missing -> ' + d.fallback}")


if __name__ == "__main__":
    main()
