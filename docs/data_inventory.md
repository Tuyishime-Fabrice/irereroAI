# Data inventory: what the team holds and what the checks found

Last intake: 28 October 2026. Checksums for every file are in
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
| MINEDUC yearbook extracts | 4 district tables (pupils, teachers, classrooms, schools) and 4 national series | MINEDUC, Education Statistical Yearbook 2024/25 (Feb 2026), Annexes 1, 7, 11, 20 and Tables 2.1.2, 2.5.5, 3.4.1, 3.5.1 | Cross-check only: the national series in `data/interim/yearbook/` | Checks the master table below |
| MINEDUC master table | `IrereroAI_MINEDUC_Master_District_Year_2020-21_to_2024-25.csv`: 30 districts × 5 school years, pupils and teachers by sex, schools, classrooms | MINEDUC yearbooks 2021/22 and 2024/25, district annexes | **Yes**: `data/raw/yearbook/mineduc_yearbook_preprimary.csv`, status *observed* | TRACK (the 2028/29 trend and status) and the capacity factor are real |
| MINEDUC validated tables | `irereroai_mineduc_validated_datasets_3.zip`: the same measures, long layout, 2021/22 to 2024/25 | MINEDUC yearbooks 2023/24 and 2024/25 | Cross-check only | Agrees with the master table in every shared cell |
| Census 2022 sector tables | `IrereroAI_Census_2022_Master_Dataset_v1.xlsx`: population, urban share, households, drinking water, lighting and grid connection by sector, with the raw thematic-report tables | NISR, PHC5 2022 thematic reports (Population, Housing): Tables D1, C1.1, C1.2, C1.3, C1.5, 3.2, 3.10 | **Yes**, merged into `data/raw/census_2022/` | The home-environment factor (water) and the peer model's urban, water, electricity and density features |
| MINEDUC school locations | `Rwandapreprimarydata_locatios.GeoJSON`: 139 schools with coordinates | MINEDUC school register | **No** | None: only standalone pre-primary schools, see below |
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

### MINEDUC master table (staged)

- **Pass.** 30 districts, 2020/21 to 2024/25, each district-year once; every name joins the
  crosswalk.
- **Sums by sex, not printed totals.** Where a printed total differs from boys + girls (or men +
  women), the sum is used and the row is listed: pupils in Nyarugenge 2023/24 (12,893 printed,
  12,863 summed), Kayonza and Kicukiro 2024/25 (±1); teachers in the eight Southern districts in
  2023/24 (each 10 below the sum). The sums reproduce the national totals: 605,229 pupils and
  10,898 teachers in 2023/24. Confirm these rows with MINEDUC before quoting them.
- **Pass.** Agrees with the earlier 2024/25 extract and with the validated tables in every shared
  cell, apart from those printed totals.
- **Pass.** District pupils add up to the national totals in 2020/21, 2021/22, 2023/24 and
  2024/25; 2022/23 is 36 short (540,962 vs 540,998). Teachers match the national staff counts
  except 2021/22 (6,347 by district vs 7,351 national).
- **Missing.** Qualified teachers are not published by district (99.4% nationally in 2024/25):
  the capacity factor uses the pupil-teacher and pupil-classroom ratios only.
- **A jump, not a typo.** Pupils rose from 355,325 (2021/22) to 540,962 (2022/23), +52% in one
  year; MINEDUC's participation rate rose from 28% (2022) to 43.7% (2023) at the same time.

### MINEDUC school locations (not staged)

139 points, all inside Rwanda, all category PRE_PRIMARY (123 private), in 21 districts, with
10,649 pre-primary pupils. MINEDUC counts 4,221 schools with pre-primary and 683,234 pupils in
2024/25: most pre-primary classes are inside primary schools, which this file does not list.
Used as the school layer it would make children near those schools look far from school, so it
is kept in `data/raw/_received/` and the distance layer stays labelled simulated. Needed: the
full school list with coordinates and a flag for schools with pre-primary classes.

### Census 2022 sector tables (staged, merged with the sample counts)

- **Pass.** 416 sectors joined by name (one census spelling, "Shyorongi", added to the reviewed
  crosswalk for the census); sector populations add up to the published national total,
  13,246,394; urban + rural = population in every sector; drinking-water shares add to 100%.
- **Derived, and how.** Improved water = the share of households using the nine sources Table
  C1.2 groups as improved × the table's household count. Electricity = households connected to
  the national grid or a mini-grid (Table C1.5 counts, not lighting). Nationally 82.3% of
  households use improved water and 52.5% are grid-connected.
- **Not at sector level in the source, so empty:** improved sanitation (Table 8.3 is by
  province), women's education (the Education thematic report is needed) and children aged 0
  to 4 (Table C4 is national). The home-environment factor rests on water alone until they
  arrive.

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

`make data` now reports simulated stand-ins for **worldpop, osm, rdhs_2025 and ncda** only.
Census 2022 (sample counts and sector tables), the projections, the yearbooks, the boundaries
and EICV7 are real.

| Part of the app | Status now | Why |
| --- | --- | --- |
| Children aged 3 to 5 in 2026, attending, places, rooms (PLAN) | **model estimate** | Census sample, NISR projections |
| Priority ranking (PLAN) | **model estimate** | Estimate, peer gap, EICV7 poverty |
| Peer benchmark (DIAGNOSE) | **model estimate** | Census attendance; no model beat the district average |
| 2028/29 trend and status (TRACK) | **model estimate** on **observed** yearbooks | MINEDUC master table |
| Share of children more than 1 km from a school | simulated | A full school list with coordinates is missing |
| Bottlenecks and factor scores (DIAGNOSE) | simulated | Wellbeing (stunting) and distance are stand-ins |

**Attendance in 2026, a stated choice.** The app can move the census 2022 rate by the
district's MINEDUC growth since 2021/22. With the real yearbooks that puts 250 of 416 sectors at
the 98% cap (88% nationally): the census rate (53.7%) and MINEDUC's gross rate barely agree by
district (correlation 0.3 to 0.4), and pupils grew 52% in 2022/23. The setting
`MINEDUC_TREND_ON_CENSUS` is therefore off: 2026 attendance is the census 2022 rate (53.5%), and
places needed may be overstated where enrolment has grown. TRACK shows MINEDUC's own gross rate
(65.3% nationally in 2024/25; 21 of 30 districts at or above 65%).

**Read TRACK with care.** The straight-line trend runs through the 2022/23 jump, so it is steep
and reaches the 100% cap in many districts; the back-test error is 5.1 points. The gross rate
counts over-age pupils.
