# Data inventory: what the team holds and what the checks found

Last intake: 24 October 2026. Checksums for every file are in
[`data/received_files.csv`](../data/received_files.csv); the full check list is written to
`data/interim/intake_report.md` each time `make intake` runs.

## How received files are kept

NISR and MINEDUC figures are cited, never redistributed. The app and the build hold
aggregates only: no child or household records. The one person-level file received (census
2022 sample records of children aged 3 to 5) stays read-only in `data/raw/_received/`; the
intake sums its weights to one count per sector, and only those counts reach the build, the
database or the screens.

| Rule | How it is applied |
| --- | --- |
| Records stay records | Person-level files are aggregated at intake (weighted counts per sector) and never copied anywhere else |
| Originals never enter git | Kept read-only in `data/raw/_received/<package>/`. `data/raw/`, `data/interim/` and `data/processed/` are gitignored, and the pre-commit hook and CI refuse them and data formats (`.dta`, `.sav`, `.parquet`, `.tif` and others) |
| Originals are never edited | Read-only copy (owner and group read only). Conversions are written beside them, never over them |
| Every file is traceable | `data/received_files.csv` (committed) records name, size, SHA-256, date and where it was staged. It holds no values. Compare a colleague's copy with `sha256sum <file>` |
| Nothing is filled in | A conversion that lacks years or columns stays in `data/interim/`; the app keeps its red SIMULATED stand-in for that dataset rather than mixing real and invented values in one series |
| Sources stay cited | Each staged row keeps its `source_page`; every number in the app and in exports shows its source, period and status |
| Small numbers | Exports show counts under 10 children as "fewer than 10" (unchanged) |
| A deployment gets aggregates only | `make bundle` zips the staged tables, never `_received/`; the zip lives in a private repository and the app checks its SHA-256 and every file before use ([deploy_private_data.md](deploy_private_data.md)) |
| On request, remove | Delete `data/raw/_received/<package>/`, `data/raw/<dataset>/` and `data/interim/`, run `make data`; the app returns to the stand-ins. The manifest rows can stay as a record of receipt, or be removed |

A cloud session's disk is temporary: the team's own copies remain the master copies. Re-run
`make intake FILES="<folder>"` on any machine that holds them; the checksums say whether the
copies are identical.

## Received

| Package | Files | Publisher, period | Staged | Effect in the app |
| --- | --- | --- | --- | --- |
| EICV7 district poverty | `eicv7_poverty.csv` (and the same table as `.xlsx`) | NISR, EICV7 Main Indicators Report 2023/24, Figure 9.1, p. 80 | **Yes**: `data/raw/eicv7/eicv7_poverty.csv`, 30 districts, status *published estimate* | Poverty in PLAN and DIAGNOSE is now real, at district level, labelled "district" |
| MINEDUC yearbook extracts | 4 district tables (pupils, teachers, classrooms, schools) and 4 national series | MINEDUC, Education Statistical Yearbook 2024/25 (Feb 2026), Annexes 1, 7, 11, 20 and Tables 2.1.2, 2.5.5, 3.4.1, 3.5.1 | **No**: converted to `data/interim/yearbook/` | None yet. TRACK and the capacity factor keep the labelled stand-in until the gaps below are filled |
| COD-AB gazetteer | `rwa_gazetteer_rphc2012_v2.xlsx` | OCHA COD-AB for Rwanda, RPHC 2012 base, via HDX | **Codes only**: `data/reference/pcodes_cod_ab.csv` and both crosswalks | All 416 sectors and 30 districts carry their codes (e.g. Muhanga RW27, Cyeza RW2701) |
| Census 2022 sample records | `children_age_3_5_clean.csv`: 107,238 records of children aged 3 to 5, with sector code, age, attendance and population weight | NISR, PHC5 2022 | **Yes**, as weighted counts: `data/raw/census_2022/`, 416 sectors and 30 district sums, `basis = sample`, status *model estimate* | The 2026 estimate is real: each sector's share of its district's children and its 2022 attendance rate come from the census |
| NISR projections | `nisr_projections_2023_2032.xlsx`: single-age, by sex, 30 districts, 2023 to 2032, with district totals | NISR, Subnational Population Projections 2023-2032 | **Yes**: `data/raw/projections/nisr_projections_2023_2032.csv`, population and children aged 3 to 5 per district and year, status *published estimate* | The 2026 estimate takes each district's children aged 3 to 5 straight from the projection (no 2022 age share held constant) |
| COD-AB boundaries | `provinces/districts/sectors.geojson` (5, 30, 416 units) and a verification report | NISR administrative boundaries via HDX (`rwa_adm_2006_NISR_WGS1984_20181002`) | **Yes**: `data/raw/boundaries/`, codes, names and shapes only | Every map uses the official shapes and NISR codes; provinces keep the app's ids and names (City of Kigali, not Kigali City) |

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

### Census 2022 sample records (staged as weighted counts)

- **Pass.** 107,238 records, weighted to 1,080,260 children aged 3 to 5 (weights 5.1 to 403.8,
  median 9.9); ages 3, 4 and 5 only; every sector code sits inside its district code; all 416
  sectors and 30 districts join the crosswalk by NISR code.
- **Pass.** 53.7% of children aged 3 to 5 attending nationally (579,989 of 1,080,237).
- **Left out, and said so.** 2 records (19 weighted children) with attendance not stated
  (code 9). They are in neither "attending" nor "never attended", so the totals are 23 below
  the sum of all weights.
- **Spelling.** RW4116 is "Shyorongi" in the census and "Shyrongi" in COD-AB and the
  crosswalk; joined by code, shown with the crosswalk spelling.
- **Uncertainty.** These are sample records, not the full count. 10 sectors rest on fewer than
  100 sampled children (fewest: Kicukiro sector, 59); their attendance rates are uncertain by
  up to about ±11 points (simple random sample approximation). 33 records carry weights above
  100 (up to 404) in Huye/Ngoma, Nyarugenge/Mageregere, Rubavu/Nyakiriba, Rusizi/Kamembe and
  Rwamagana/Muhazi: those sectors' counts lean on few households.
- **Expected, not an error.** 56,132 rows repeat another row exactly: children of the same age,
  sector, attendance and weight are identical in a file with these few columns.
- **Status.** A weighted tabulation by IrereroAI is a *model estimate*, not an *observed*
  count; the loader sets it from `basis = sample`. Printed Table 2.5 counts, if they arrive,
  are *observed* and take over.
- **Not in this file.** Population, children 0 to 4, households, water, sanitation,
  electricity, urban share and women's education. The home-environment factor shows "no
  data", and the peer model works with poverty and child density only.
- **Check later.** The district rows are sums of the sectors, so the "sectors add up" check
  cannot catch an error here. Compare them with the printed Table 2.5 district totals.

### NISR projections (staged)

- **Pass.** Female + male = both sexes in every cell; the single ages add up to the printed
  district totals for all 300 district-years; 30 districts, 2023 to 2032, no repeated cells.
- **Pass.** Four districts were supplied more than once (Nyanza, Rwamagana, Nyagatare,
  Kirehe); the workbook's own check says the copies are identical.
- **Pass.** Rwanda 13,499,134 in 2023 to 16,423,031 in 2032; children aged 3 to 5 1,030,575 to
  1,168,810.
- **One projection only.** The variant is not stated; it is read as the main (medium) one. The
  2026 range uses the default projection error instead of low and high variants.
- **Cross-check.** Projected children aged 3 to 5 in 2023 (1,030,575) are 4.6% below the
  census sample's 2022 count (1,080,237). The estimate takes district totals from the
  projection, and only the split across sectors and the attendance rate from the census, so
  the two are never added.

### COD-AB boundaries (staged)

- **Pass.** 5 provinces, 30 districts, 416 sectors; no duplicate codes, no empty shapes; every
  district and sector code is in the reviewed crosswalk; every parent exists; every sector's
  code starts with its district's; every sector lies inside the district its code names.
- **Repaired.** One sector shape had a self-intersection, fixed with `make_valid`.
- **Pass.** Names match the crosswalk spelling exactly. Sectors cover 24,354 km² (land; Rwanda
  is about 26,300 km² with its lakes).
- **Kept.** Only the code, name, parent code and shape; the other attributes (French and
  Kinyarwanda names, ADM columns) stay in the originals.
- **Check later.** The source says the dataset (2006 administrative structure, published in
  2018) has not been reviewed for changes in the last 12 months; confirm against current NISR
  sources before a production release.

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

`make data` now reports simulated stand-ins for **worldpop, osm, yearbook, rdhs_2025 and
ncda**. Census 2022, the projections, the boundaries and EICV7 are real.

| Part of the app | Status now | Why |
| --- | --- | --- |
| Children aged 3 to 5 in 2026, attending, places, rooms (PLAN) | **model estimate** | Census sample, NISR projections |
| Priority ranking (PLAN) | **model estimate** | Estimate, peer gap (census, poverty, density), EICV7 poverty |
| Peer benchmark (DIAGNOSE) | **model estimate** | Census attendance; no model beat the district average |
| Share of children more than 1 km from a school | simulated | School points (OpenStreetMap) missing |
| Bottlenecks and factor scores (DIAGNOSE) | simulated | Capacity (yearbook), wellbeing (stunting) and distance are stand-ins |
| 2028/29 trend and status (TRACK) | simulated | Yearbook series incomplete |

Each screen now labels each part with its own status, so a real estimate sits next to a
labelled SIMULATED distance or trend. The red SIMULATED notice stays on any screen that shows
a simulated value.

**Method change, stated in the app.** While the census is real and the yearbook is not,
attendance in 2026 is the census 2022 rate: a real census is never moved by a simulated
MINEDUC trend. Enrolment growth since 2022 is therefore not yet in the 2026 figures, and places
needed may be overstated where enrolment has grown. The trend applies again once the yearbook
series is complete.
