"""Registry of source adapters.

python -m pipelines.registry            # list sources, expected files and target tables
python -m pipelines.registry --write    # regenerate docs/PHASE2_SOURCES.md from the specs
python -m pipelines.registry --check    # fail if docs/PHASE2_SOURCES.md is out of date
"""

import argparse
import sys

from pipelines.adapter import REPO_ROOT, SourceAdapter
from pipelines.adapters.boundaries import Boundaries
from pipelines.adapters.census_2022 import Census2022
from pipelines.adapters.education_yearbook import EducationYearbook
from pipelines.adapters.eicv7 import Eicv7
from pipelines.adapters.lfs_2025 import Lfs2025
from pipelines.adapters.ncda_mapping import NcdaMapping
from pipelines.adapters.osm import Osm
from pipelines.adapters.rdhs_2019_gps import Rdhs2019Gps
from pipelines.adapters.rdhs_2025 import Rdhs2025
from pipelines.adapters.worldpop import WorldPop

ADAPTERS: dict[str, type[SourceAdapter[object, object]]] = {
    cls.spec.name: cls
    for cls in (
        Census2022,
        Eicv7,
        Rdhs2025,
        Rdhs2019Gps,
        Lfs2025,
        EducationYearbook,
        NcdaMapping,
        WorldPop,
        Osm,
        Boundaries,
    )
}


SOURCES_DOC = REPO_ROOT / "docs" / "PHASE2_SOURCES.md"


def sources_markdown() -> str:
    lines = [
        "# Phase 2 sources",
        "",
        "Generated from the adapter specs by `python -m pipelines.registry --write`; do not edit.",
        "How to implement an adapter is in [PHASE2_HANDOFF.md](PHASE2_HANDOFF.md).",
        "",
        "| Adapter | Source | Origin | Target tables |",
        "| --- | --- | --- | --- |",
    ]
    for name, cls in ADAPTERS.items():
        spec = cls.spec
        tables = ", ".join(f"`{t}`" for t in spec.target_tables)
        lines.append(f"| [`{name}`](#{name}) | {spec.title} | {spec.origin.value} | {tables} |")
    for name, cls in ADAPTERS.items():
        spec = cls.spec
        year = spec.reference_year if spec.reference_year is not None else "extract date"
        lines += [
            "",
            f'<a id="{name}"></a>',
            "",
            f"## {spec.title}",
            "",
            f"- Adapter: `pipelines/adapters/{name}.py` (`{cls.__name__}`)",
            f"- Publisher: {spec.publisher}",
            f"- Reference year: {year}",
            f"- Origin: `{spec.origin.value}`",
            f"- Licence: {spec.licence}",
        ]
        if spec.url:
            lines.append(f"- Where to get it: <{spec.url}>")
        lines += ["", "Expected files (never committed):", ""]
        lines += [f"- `data/raw/{e.pattern}`: {e.description}" for e in spec.expected_files]
        lines += ["", "Writes to: " + ", ".join(f"`{t}`" for t in spec.target_tables)]
        if spec.indicators:
            lines += ["", "Indicators: " + ", ".join(f"`{i}`" for i in spec.indicators)]
        lines += ["", "Checks (loading stops if any fails):", ""]
        lines += [f"- `{c.name}`: {c.description}" for c in spec.checks]
        if spec.notes:
            lines += ["", spec.notes]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="regenerate docs/PHASE2_SOURCES.md")
    group.add_argument("--check", action="store_true", help="fail when the document is stale")
    args = parser.parse_args()
    if args.write:
        SOURCES_DOC.write_text(sources_markdown())
        return
    if args.check:
        if not SOURCES_DOC.exists() or SOURCES_DOC.read_text() != sources_markdown():
            sys.exit(f"{SOURCES_DOC.relative_to(REPO_ROOT)} is stale: run --write")
        return
    for name, cls in ADAPTERS.items():
        spec = cls.spec
        print(f"{name}: {spec.title} ({spec.publisher})")
        for expected in spec.expected_files:
            print(f"  file   data/raw/{expected.pattern}  {expected.description}")
        print(f"  tables {', '.join(spec.target_tables)}")


if __name__ == "__main__":
    main()
