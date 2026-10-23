# Data inventory: what the team holds and what the checks found

Last intake: 23 October 2026. Checksums for every file are in
[`data/received_files.csv`](../data/received_files.csv); the full check list is written to
`data/interim/intake_report.md` each time `make intake` runs.

## How received files are kept

NISR and MINEDUC figures are cited, never redistributed. IrereroAI holds published aggregates
only: no microdata, no child or household records.

| Rule | How it is applied |
| --- | --- |
| Originals never enter git | Kept read-only in `data/raw/_received/<package>/`. `data/raw/`, `data/interim/` and `data/processed/` are gitignored, and the pre-commit hook and CI refuse them and data formats (`.dta`, `.sav`, `.parquet`, `.tif` and others) |
| Originals are never edited | Read-only copy (owner and group read only). Conversions are written beside them, never over them |
| Every file is traceable | `data/received_files.csv` (committed) records name, size, SHA-256, date and where it was staged. It holds no values. Compare a colleague's copy with `sha256sum <file>` |
| Nothing is filled in | A conversion that lacks years or columns stays in `data/interim/`; the app keeps its red SIMULATED stand-in for that dataset rather than mixing real and invented values in one series |
| Sources stay cited | Each staged row keeps its `source_page`; every number in the app and in exports shows its source, period and status |
| Small numbers | Exports show counts under 10 children as "fewer than 10" (unchanged) |
| On request, remove | Delete `data/raw/_received/<package>/`, `data/raw/<dataset>/` and `data/interim/`, run `make data`; the app returns to the stand-ins. The manifest rows can stay as a record of receipt, or be removed |

A cloud session's disk is temporary: the team's own copies remain the master copies. Re-run
`make intake FILES="<folder>"` on any machine that holds them; the checksums say whether the
copies are identical.

## Received

| Package | Files | Publisher, period | Staged | Effect in the app |
| --- | --- | --- | --- | --- |
| EICV7 district poverty | `eicv7_poverty.csv` (and the same table as `.xlsx`) | NISR, EICV7 Main Indicators Report 2023/24, Figure 9.1, p. 80 | **Yes**: `data/raw/eicv7/eicv7_poverty.csv`, 30 districts, status *published estimate* | Poverty in PLAN and DIAGNOSE is now real, at district level, labelled "district" |
| MINEDUC yearbook extracts | 4 district tables (pupils, teachers, classrooms, schools) and 4 national series | MINEDUC, Education Statistical Yearbook 2024/25 (Feb 2026), Annexes 1, 7, 11, 20 and Tables 2.1.2, 2.5.5, 3.4.1, 3.5.1 | **No**: converted to `data/interim/yearbook/` | None yet. TRACK and the capacity factor keep the labelled stand-in until the gaps below are filled |
| COD-AB gazetteer | `rwa_gazetteer_rphc2012_v2.xlsx` | OCHA COD-AB for Rwanda, RPHC 2012 base, via HDX | **Codes only**: `data/reference/pcodes_cod_ab.csv` and both crosswalks | All 416 sectors and 30 districts now carry their codes (e.g. Muhanga RW27, Cyeza RW2701), so the official COD-AB boundary files will load once they are added |

## What the checks found

### EICV7 (staged)

- **Pass.** 30 districts, each once, all joined through the reviewed crosswalk; rates between
  6.8% (Nyarugenge) and 51.4% (Nyamagabe), converted from percent to shares.
- **Check against the source.** The values were read from a chart. The file's own note says
  the report text gives different figures for **Gisagara and Nyamasheke**; confirm both
  against the EICV7 district tables before the figures are used in a brief.
- **Check against the source.** Two pairs share a value exactly: Muhanga and Ruhango (15.0%),
  Kamonyi and Nyaruguru (39.7%). Ties happen, but chart readings tie more often than real
  values do.
- **Effect on method, stated in the app.** District rates mean every sector in a district has
  the same poverty value, so the poverty component no longer separates sectors *within* a
  district in the priority index, and the poverty factor in DIAGNOSE is district context.
  Sector rates, if NISR publishes them, would restore both.

### MINEDUC yearbook (not staged)

The province and national rows were checked against their districts, and boys + girls (male +
female) against each total. The transcription is otherwise clean; these rows need checking
against the PDF before use:

| Table | Row | Found | Likely reading |
| --- | --- | --- | --- |
| Pupils 2023/24 (Annex) | Nyarugenge | total 12,893, but boys 6,533 + girls 6,330 = 12,863 | **12,863**: with it, Kigali City (59,645) and Rwanda (605,229) add up exactly |
| Teachers 2023/24 (Annex) | All 8 Southern districts and the South row | each total is 10 below male + female (e.g. Muhanga 357 vs 40 + 327 = 367) | Probably the totals: male + female gives Rwanda 10,898, the figure in the staff-qualifications table (Table 3.5.1); the printed totals give 10,818 |
| Pupils 2024/25 | Kayonza, Kicukiro, East row | differ from boys + girls by 1 | Rounding in the printed table; harmless |

Other findings:

- **Spelling.** "Kigali city" (classrooms) and "Kigali City" (other tables); matched without
  regard to case, no action needed.
- **Series break.** Children in ECD centres rise 3.5 times from 2020/21 (297,021) to 2021/22
  (1,033,011): a change in what is counted, not growth. Do not trend across it. These are NCDA
  style counts and are never added to pre-primary enrolment.
- **Two different rates.** `participation_rate_ages_3_5` (54.0% in 2025) is a calendar-year
  MINEDUC rate; IrereroAI tracks a gross rate (pupils per child aged 3 to 5) by school year.
  They are not interchangeable and are not mixed.
- **Qualified teachers** are national only (99.4% qualified in 2024/25). The capacity factor
  needs them by district; at 99% nationally the district spread may be small.

What the yearbook still needs before it can replace the stand-in: district tables for
**2020/21 and 2021/22**, pupils and teachers for **2022/23**, and **qualified teachers by
district** for every year. See [data_requests.md](data_requests.md#3-mineduc-yearbooks).

### COD-AB gazetteer (codes)

- **Pass.** 5 provinces, 30 districts, 416 sectors, no duplicate codes; every sector and
  district name matches the crosswalk exactly, so no spelling had to be guessed. Each sector
  code starts with its district code (tested).
- The crosswalk rows stay `reviewed = no`: a person confirms them.
- **Incomplete sheet.** The cell sheet (ADM4) stops at 1,000 rows and covers 16 districts;
  Rwanda has about 2,150 cells. IrereroAI works at sector level and does not use it.
- **Licence.** The repository declares COD-AB as CC BY 4.0; confirm the licence shown on the
  HDX page for this gazetteer and cite it with the codes.

## Status after intake

`make data` now reports simulated stand-ins for census_2022, worldpop, projections, osm,
yearbook, rdhs_2025 and ncda; EICV7 is real; boundaries are real geoBoundaries shapes with all
416 sector codes. Every screen still shows the red SIMULATED notice, because the 2026 estimate
rests on the census, projections and yearbooks.
