# Data

| Folder | Contents | In git |
| --- | --- | --- |
| `raw/<dataset>/` | Source files you add, one folder per dataset in [DATA_SOURCES.md](../DATA_SOURCES.md) | no |
| `raw/_received/<package>/` | Read-only copies of files exactly as received, kept by `make intake` | no |
| `received_files.csv` | What the team holds: file name, size, SHA-256, date received and where it was staged. Metadata only, no values | yes |
| `interim/` | Tables parsed from PDFs (census Table 2.5) | no |
| `processed/` | Parquet and simplified GeoJSON written by `make data` | no |
| `demo/` | Stand-ins in the same formats as the real files: simulated tables (seed 2026) and simplified geoBoundaries shapes | yes |
| `reference/` | Reviewed crosswalks from source spellings to `geo_id` and NISR codes; `pcodes_cod_ab.csv`, the province, district and sector codes from the COD-AB gazetteer | yes |

## Receiving files

Files that arrive as tables in their own layout (the EICV7 district chart, the MINEDUC yearbook
annexes) go through `make intake FILES="<file or folder> ..."`. It keeps the original read-only
in `raw/_received/`, records its checksum in `received_files.csv`, converts it to the declared
columns through the crosswalks, and checks it: districts once each, parts adding to totals,
district rows adding to province and national rows, breaks in a series. A converted table goes
into `raw/<dataset>/` only when it is complete; otherwise it waits in `interim/` and
`interim/intake_report.md` lists what is missing. Nothing is filled in or estimated. See
[docs/data_inventory.md](../docs/data_inventory.md) for what has been received and checked, and
[docs/data_requests.md](../docs/data_requests.md) for what is still needed.

Run `make sources` to create the `raw/` folders and see which files are present, then
`make data` to load them. A dataset whose file is missing is read from `demo/`, and every value
from it carries the status **simulated**: shown with a red SIMULATED badge and left out of
exports by default.

`demo/` is regenerated with `uv run python -m irerero.data.demo_bundle` (needs the geoBoundaries
files in `raw/geoboundaries/`); the output is committed so the app runs without any downloads.

NISR licences forbid redistributing microdata. Raw files stay on the machine that holds them.
The pre-commit hook and CI block data formats (`.dta`, `.sav`, `.tif`, `.pbf`, `.parquet` and
others) and anything under `raw/`, `interim/` or `processed/`.
