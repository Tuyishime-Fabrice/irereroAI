"""Write DATA_SOURCES.md from the dataset specs.

python -m pipelines.sources            # create data/raw/<dataset>/ folders, list what is present
python -m pipelines.sources --write    # regenerate DATA_SOURCES.md
python -m pipelines.sources --check    # fail if DATA_SOURCES.md is out of date (used in tests)
"""

import argparse
import sys

from pipelines.runs import RAW_DIR, REPO_ROOT
from pipelines.sources import DATASETS
from pipelines.sources.spec import Dataset

DOC = REPO_ROOT / "DATA_SOURCES.md"
TYPES = {
    "text": "text",
    "integer": "whole number ≥ 0",
    "number": "number",
    "share": "share, 0 to 1",
    "date": "date, YYYY-MM-DD",
    "boolean": "yes / no",
}


def _section(number: int, d: Dataset) -> list[str]:
    lines = [
        "",
        f'<a id="{d.key}"></a>',
        "",
        f"## {number}. {d.title}",
        "",
        f"- **Folder:** `data/raw/{d.key}/`",
        f"- **Publisher:** {d.publisher}",
        f"- **How to get it:** {d.access}" + (f" — <{d.url}>" if d.url else ""),
        f"- **Licence:** {d.licence}",
        f"- **Origin label:** `{d.origin.value}`",
        f"- **Geographic level:** {d.level}",
        f"- **Joins on:** {d.joins_on}",
        f"- **Used by:** {'; '.join(d.used_by)}",
        f"- **Writes:** {'; '.join(d.produces)}",
        f"- **If missing:** {d.fallback}",
        "",
        "| File | Format | Contents |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| `{f.name}` | {f.format} | {f.description}{'' if f.required else ' (optional)'} |"
        for f in d.files
    ]
    if d.columns:
        lines += ["", "| Column | Type | Required | Meaning |", "| --- | --- | --- | --- |"]
        lines += [
            f"| `{c.name}` | {TYPES[c.type]} | {'yes' if c.required else 'no'} | {c.description} |"
            for c in d.columns
        ]
    for note in d.notes:
        lines += ["", note]
    return lines


def document() -> str:
    lines = [
        "# Data sources",
        "",
        "Generated from the dataset specs in `pipelines/sources/` by "
        "`python -m pipelines.sources --write`; do not edit by hand.",
        "",
        "Put each file in its folder under `data/raw/` and run the build "
        "(`make build`, or `make seed` with Docker). The folder is ignored by git: NISR and DHS "
        "licences forbid redistribution, so data never enters the repository.",
        "",
        "Every dataset is optional. When a file is missing, the build uses the current demo "
        "data in its place, stored with `origin = simulated`, and every screen that shows it "
        "carries the SIMULATED DATA badge. When a file is present but does not match its "
        "columns, the build stops and says which row and column to fix.",
        "",
        "Area files join on the official NISR admin code (`admin_code`) at the level in "
        "`admin_level`. Until the official boundaries are loaded, the demo boundaries have no "
        "official codes, so give `admin_name` instead; names are matched within their level, "
        "ignoring case and accents. Sector names repeat across districts, so add the district "
        "in `parent_name` when a name is shared.",
        "",
        "Rasters and the OpenStreetMap extract need the geo extras: `uv sync --extra geo`.",
        "",
        "```",
        "data/",
        "  raw/                    (gitignored)",
    ]
    lines += [f"    {d.key + '/':22}  {', '.join(f.name for f in d.files)}" for d in DATASETS]
    lines += [
        "  contract/               JSON Schemas of the database tables (generated)",
        "```",
        "",
        "| # | Dataset | Level | Used by | If missing |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {i} | [{d.title}](#{d.key}) | {d.level} | {'; '.join(d.used_by)} | {d.fallback} |"
        for i, d in enumerate(DATASETS, start=1)
    ]
    for i, d in enumerate(DATASETS, start=1):
        lines += _section(i, d)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="regenerate DATA_SOURCES.md")
    group.add_argument("--check", action="store_true", help="fail when the document is stale")
    args = parser.parse_args()
    if args.write:
        DOC.write_text(document())
    elif args.check:
        if not DOC.exists() or DOC.read_text() != document():
            sys.exit("DATA_SOURCES.md is stale: run python -m pipelines.sources --write")
    else:
        for d in DATASETS:
            (RAW_DIR / d.key).mkdir(parents=True, exist_ok=True)
            print(f"{d.key:20} {'present' if d.present(RAW_DIR) else 'missing: ' + d.fallback}")


if __name__ == "__main__":
    main()
