# Data

| Folder | Contents | In git |
| --- | --- | --- |
| `raw/<dataset>/` | Source files you add, one folder per dataset in [DATA_SOURCES.md](../DATA_SOURCES.md) | no |
| `interim/` | Tables parsed from PDFs (census Table 2.5) | no |
| `processed/` | Parquet and simplified GeoJSON written by `make data` | no |
| `demo/` | Stand-ins in the same formats as the real files: simulated tables (seed 2026) and simplified geoBoundaries shapes | yes |
| `reference/` | Reviewed crosswalks from source spellings to `geo_id` and NISR codes | yes |

Run `make sources` to create the `raw/` folders and see which files are present, then
`make data` to load them. A dataset whose file is missing is read from `demo/`, and every value
from it carries the status **simulated**: shown with a red SIMULATED badge and left out of
exports by default.

`demo/` is regenerated with `uv run python -m irerero.data.demo_bundle` (needs the geoBoundaries
files in `raw/geoboundaries/`); the output is committed so the app runs without any downloads.

NISR licences forbid redistributing microdata. Raw files stay on the machine that holds them.
The pre-commit hook and CI block data formats (`.dta`, `.sav`, `.tif`, `.pbf`, `.parquet` and
others) and anything under `raw/`, `interim/` or `processed/`.
