"""Pre-commit guard: blocks large files and data formats that must never enter git.

NISR microdata licences forbid redistribution, so the guard fails closed on data formats
even when they are small.
"""

import sys
from pathlib import Path

MAX_BYTES = 500 * 1024
BLOCKED_SUFFIXES = {
    ".dta", ".sav", ".tif", ".tiff", ".pbf", ".gpkg", ".shp", ".parquet", ".pkl", ".zip"
}  # fmt: skip
BLOCKED_DIRS = ("data/raw/", "data/interim/", "data/processed/", "data/bundle/")
ALLOWED_LARGE = {"uv.lock"}


def problems(paths: list[str]) -> list[str]:
    found = []
    for name in paths:
        path = Path(name)
        posix = path.as_posix()
        if path.suffix.lower() in BLOCKED_SUFFIXES or posix.startswith(BLOCKED_DIRS):
            found.append(f"{posix}: data files are never committed (see data/README.md)")
        elif path.is_file() and path.stat().st_size > MAX_BYTES and path.name not in ALLOWED_LARGE:
            size_kb = path.stat().st_size // 1024
            found.append(f"{posix}: {size_kb} KB exceeds the {MAX_BYTES // 1024} KB limit")
    return found


if __name__ == "__main__":
    errors = problems(sys.argv[1:])
    for error in errors:
        print(error, file=sys.stderr)
    sys.exit(1 if errors else 0)
