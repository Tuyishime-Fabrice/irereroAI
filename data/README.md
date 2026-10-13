# Data

Nothing in this folder is committed except this file and `contract/`.

| Folder | Contents | In git |
| --- | --- | --- |
| `contract/` | JSON Schemas for every dataset the pipelines load | yes |
| `raw/` | Downloaded source files: `geoboundaries/` today, NISR microdata in Phase 2 | no |
| `interim/` | Cleaned, aligned intermediate files | no |
| `processed/` | Model inputs and outputs | no |

NISR microdata licences forbid redistribution. Raw files stay on the machine that downloaded
them. The pre-commit hook and CI block data formats (`.dta`, `.sav`, `.tif`, `.pbf` and others)
anywhere in the repository.
