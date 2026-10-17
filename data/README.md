# Data

Nothing in this folder is committed except this file and `contract/`.

| Folder | Contents | In git |
| --- | --- | --- |
| `raw/<dataset>/` | Source files you add: one folder per dataset in [DATA_SOURCES.md](../DATA_SOURCES.md) | no |
| `raw/geoboundaries/` | geoBoundaries shapes, downloaded by the build while official boundaries are missing | no |
| `contract/` | JSON Schemas of the database tables (generated) | yes |

Run `make sources` to create the `raw/` folders and see which files are present, then
`make build` to load them. Anything missing is stood in for by demo data, labelled simulated.

NISR microdata licences forbid redistribution. Raw files stay on the machine that downloaded
them. The pre-commit hook and CI block data formats (`.dta`, `.sav`, `.tif`, `.pbf` and others)
anywhere in the repository.
