# Data inventory: what the team holds, its status, and what the checks found

Last intake: **30 October 2026** (the files uploaded to the private data repository that day,
including the DHS 2025 and EICV7 microdata uploaded in the afternoon).
Earlier deliveries (23 to 28 October) are kept below. Checksums for every file are in
[`data/received_files.csv`](../data/received_files.csv); the full check list is written to
`data/interim/intake_report.md` each time `make intake` runs.

## Where the data lives and how the deployed app reads it

| Part | What it is |
| --- | --- |
| App repository | `Tuyishime-Fabrice/irereroAI` (public), deployed on Streamlit Community Cloud from `app/streamlit_app.py`. It holds **no** received data: code, the labelled demo bundle (`data/demo/`), crosswalks and this record of checksums |
| Data repository | `Tuyishime-Fabrice/irereroai-data` (private), branch `main`. Holds the private **bundle** the app downloads (`irerero-data.zip`, staged aggregates only), the school list (`schools/`) and, from 30 October, the received originals |
| How the app gets it | The GitHub **Contents API** (`api.github.com/repos/.../contents/...`, raw media type) with a fine-grained, read-only token. No git clone, no Git LFS, no raw.githubusercontent URLs |
| Settings | Streamlit **Secrets**: `IRERERO_DATA_URL` (the bundle's API address), `IRERERO_DATA_TOKEN`, `IRERERO_DATA_SHA256` (the bundle's checksum, so a swapped file is refused), `IRERERO_SCHOOLS_PATH` (the school list's path in the same repository) |
| Refresh | On first start the app downloads the bundle, checks the SHA-256 and every file against its manifest, unpacks it to `data/raw/`, and builds the tables. It rebuilds whenever the bundle or school-list checksum changes; it never mixes an old build with new data |

Uploading a file to the data repository does **not** reach the app by itself: the app reads only
the bundle named in `IRERERO_DATA_URL` and the school list named in `IRERERO_SCHOOLS_PATH`. New
received files go through `make intake` (checks and conversion), `make data` (build) and
`make bundle` (the zip the app downloads). See [deploy_private_data.md](deploy_private_data.md).

## Status legend

| Status | Meaning |
| --- | --- |
| Awaiting upload | Expected, not yet in the data repository |
| Uploaded | In the data repository, not yet opened |
| Inspected | Opened; structure, metadata and fields recorded |
| Validated | Passed the intake checks (counts, codes, joins, ranges, duplicates, agreement with other sources) |
| Integrated | Converted and staged in `data/raw/`, read by the app's loaders, in the private bundle |
| Replacement verified | Integrated, the app built and every screen rendered on it, and the outputs compared with the data it replaces |
| Verification only | Validated, used to check a staged table; the app does not read it (it is national, district-only or in age groups the app cannot use) |
| Blocked | Cannot be used yet: incomplete, or access or licensing terms unresolved |

"Real" means the values come from the publisher's file; "derived" means IrereroAI computed them
from real values by a stated method; "provisional" means real but known to be partial;
"simulated" means invented stand-ins, always shown with the red SIMULATED badge.

## Inventory by function

### PLAN

| Dataset | Source; reference | Received file(s) | Status | Nature; how the app uses it | Known limitations |
| --- | --- | --- | --- | --- | --- |
| PHC5 population indicators | NISR, census night 15 Aug 2022 | `PHC5-2022_Main_Indicators.xlsx` (101 sheets) | Verification only | Real. Confirms the staged census sector table: 416 of 416 sector populations, 30 district populations and households identical | Census 2022 counts are never shown as 2026 counts; the 2026 estimate takes district totals from the projections |
| Census 3-5 attendance by sector | NISR, PHC5 2022 sample records (24 Oct) | `children_age_3_5_clean.csv` (kept on the receiving machine) | Integrated | Derived (weighted tabulation, *model estimate*): each sector's share of its district's children and its 2022 attendance rate | Sample-based; 10 sectors rest on fewer than 100 sampled children |
| WorldPop population distribution | WorldPop, Univ. of Southampton; 2020 constrained UN-adjusted and 2026 R2025A, 100 m | 9 GeoTIFFs (see below); 6 re-uploaded on 30 Oct are byte-identical copies | **Blocked (incomplete)** | Not used. The app keeps its documented stand-in: sector shares of the census count, children spread evenly inside a sector | Each set lacks the male 1-4 layer: `rwa_m_1_2020_constrained_UNadj.tif`, `rwa_m_01_2026_CN_100m_R2025A_v1.tif` |
| NISR population projections | NISR, Subnational Population Projections 2023-2032 | single-age district workbook (24 Oct); `2.7 Muhanga_single_age.xlsx`, five province workbooks (30 Oct) | Integrated (district single ages); new workbooks verification only | Real (*published estimate*). 2026 children aged 3-5 per district; denominators for TRACK | One variant only (read as medium). Province workbooks are in 5-year groups (0-4, 5-9) and cannot give ages 3-5 |
| Administrative boundaries | NISR via HDX; 2022 sector layer (published 3 Sep 2024) | `Rwanda_Sector_Boundaries_2022.geojson` | **Replacement verified** | Real. Replaces the COD-AB 2006-structure shapes (published 2018). Every map and spatial join; districts and provinces are the union of their sectors | Licence of the 2022 layer to confirm on its HDX page (COD-AB is CC BY 4.0) |
| MINEDUC school locations | MINEDUC school register; export date not stated | `rwanda_preprimary_schools.geojson`, `rwanda_preprimary_schools.csv` (same 139 records as `schools/Rwandapreprimarydata_locatios.GeoJSON`) | Integrated, **provisional** | Real, partial. School map and the share of children > 1 km from a *listed* school (an upper bound) | Standalone pre-primary schools only (139 of 4,221 schools with pre-primary); 8 points lie in another district than their record names |
| OpenStreetMap Rwanda extract | OSM contributors via Geofabrik; data as of 29 Oct 2026, 21:21 UTC | `rwanda-261029.osm.pbf` (68 MB; 23 MB staged: schools and walkable roads) | **Replacement verified** | Real (ODbL 1.0). Walking distance along 174,739 roads and paths in 407 of 416 sectors; 592 mapped schools join the MINEDUC list (4 at the same site counted once): 727 schools | Partial: 592 mapped schools, and OSM does not say which have pre-primary; the distance stays provisional, an upper bound |
| EICV7 poverty | NISR, EICV7 2023/24 Main Indicators Report, Fig. 9.1 (23 Oct); microdata (30 Oct) | `eicv7_poverty.csv`; `Microdata.zip` (`CS_EICV7_poverty_file.dta` used) | Integrated; microdata verification only | Real (*published estimate*), district rates; poverty component of the priority index. The microdata reproduce all 30 rates within 0.05 points | District level only: EICV7 is not designed for sector estimates |
| ECD standards and capacity parameters | NCDA, National ECD Standards 2024 | none (parameters in `irerero/config.py`) | Unchanged | Policy parameters, not observations: 30 children per room, 1 caregiver per 15-30 children, 1 km | The source pages of each parameter are still to be cited; no standards document was uploaded |

### DIAGNOSE

| Dataset | Source; reference | Received file(s) | Status | Nature; how the app uses it | Known limitations |
| --- | --- | --- | --- | --- | --- |
| PHC5 household indicators | NISR, PHC5 2022 thematic reports (28 Oct); Main Indicators (30 Oct) | `IrereroAI_Census_2022_Master_Dataset_v1.xlsx`; Main Indicators Tables 58, 68, 71, 74 | Integrated (sector water, grid electricity, households, urban share); Main Indicators verification only | Real by sector: home-environment factor and peer-model features | Sanitation (Table 71) and any-source electricity (Table 74) are district only: never copied to sectors, so sanitation stays empty |
| DHS 2025 wellbeing indicators | NISR, MoH, The DHS Program; interviews in 2025 (phase RW8) | `Microdata (1).zip` (11 recode files; `RWPR91FL.dta` used) | **Replacement verified** | Derived (*model estimate*): stunting under 5 by district with 95% intervals, weighted IrereroAI tabulation following DHS definitions. Drives the wellbeing factor and the nutrition trigger | Districts rest on 178-362 children (intervals ±3.9 to ±9.8 points); compare with the DHS 2025 report before quoting; district context, never a child's status |
| EICV7 poverty indicators | NISR | as in PLAN | Integrated | District context in the poverty factor | as in PLAN |
| MINEDUC capacity and staffing | MINEDUC yearbooks 2020/21-2024/25 (28 Oct district master table); national workbook (30 Oct) | `IrereroAI_MINEDUC_Master_District_Year_2020-21_to_2024-25.csv`; `Rwanda_MINEDUC_PrePrimary_2020-21_to_2024-25.xlsx` | Integrated (district table); workbook verification only | Real (*observed*): pupil-teacher and pupil-classroom ratios by district | The workbook is national and a transcription (its own Read_Me says so); qualified teachers are national only (99.4% in 2024/25) |
| ECD centres and services | NCDA ECD Mapping System | `ncda_ecd_mapping_extract.csv` | Integrated (display off) | Real: 34,448 active services in all 30 districts, staged in the `supply_extract` schema | Not used in DIAGNOSE scores; shown on screen only when `IRERERO_NCDA_DISPLAY` is on |

### TRACK

| Dataset | Source; reference | Received file(s) | Status | Nature; how the app uses it | Known limitations |
| --- | --- | --- | --- | --- | --- |
| MINEDUC annual enrolment and capacity | MINEDUC yearbooks 2020/21-2024/25 | district master table (28 Oct); national workbook (30 Oct) | Integrated (district); national verification | Real (*observed*): pupils by district and year, the 2028/29 trend | The national workbook confirms 5 of 5 years of schools and classrooms and 4 of 5 years of pupils and teachers (see below) |
| Population projection denominators | NISR projections 2023-2032 | as in PLAN | Integrated; Muhanga and province tables verification | Real (*published estimate*): children aged 3-5 per district and year | as in PLAN |

### LEARN

| Dataset | Source; reference | Received file(s) | Status | Nature; how the app uses it | Known limitations |
| --- | --- | --- | --- | --- | --- |
| NCDA ECD Mapping extract | NCDA; extract date 30 Oct 2026 (visits 18 Oct 2023 to 26 Aug 2025) | `ncda_ecd_mapping_extract.csv` (37,431 records; no GeoJSON was uploaded) | Integrated (display off) | Real: 1,044 active services in Muhanga. Loaded beside the demo centres; not added to the distance layer | Data-sharing agreement to confirm before display; not a live feed; no capacity, enrolment counts ages 3-6 |
| Course definitions and lessons | NCDA, UNICEF, WHO (adapted, cited) | `content/courses/` (in the app repository) | Unchanged | Application content: 4 courses, 13 lessons, 20 quiz items, triggers and completion rules | Kinyarwanda drafts await review |
| Caregiver check-ins and course progress | IrereroAI demo generator, seed 2026 | none | **Simulated, demo mode only** | Fictional caregivers at 36 simulated Muhanga centres, every row labelled SIMULATED | No real operational records exist yet; the screens say so |

## What the 30 October checks found

Numbers from `make intake`; nothing was filled in or guessed, and every exclusion is counted.

### Administrative boundaries, NISR 2022 sector layer (replaces COD-AB)

- **Pass.** 416 sectors, codes RW1101 to RW5715, each once; every sector sits in
  one district and every district in one province; every code is in the reviewed crosswalk;
  0 sectors outside the district their code names. EPSG:4326. Last edited by the publisher on
  3 September 2024 (`NISR_Publisher`).
- **Repaired.** 6 self-intersecting shapes (Kigabiro, Maraba, Musebeya, Muyira, Ruharambuga,
  Rurembo), fixed with `make_valid`; nothing dropped.
- **Derived, and how.** Districts (30) and provinces (5) are the union of their sectors by
  official code; their area equals the sectors' to 0.01 km².
- **Compared with the shapes they replace.** Same 416 codes; median overlap 0.992 (intersection
  over union); 57 sectors below 0.98, 5 below 0.9 (Nyamasheke/Rangiro 0.73, Huye/Gishamvu 0.73,
  Nyamasheke/Bushekeri 0.81, Huye/Ruhashya 0.84, Nyabihu/Mukamira 0.90): boundaries were
  redrawn there. Total
  land area unchanged (24,354 km²).
- **Name.** RW4116 is "Shyorongi" in the 2022 layer and the census, "Shyrongi" in COD-AB; the
  app now shows "Shyorongi". Joins are by code, so nothing else changes.

### MINEDUC school locations (provisional)

- **The same list.** `rwanda_preprimary_schools.geojson` holds the same 139 schools, attributes
  and points as the copy already in use (`schools/Rwandapreprimarydata_locatios.GeoJSON`); the
  CSV is an attribute export of the same records (coordinates identical). One copy is staged, so
  no school is counted twice.
- **Pass.** 139 of 139 loaded, 0 invalid coordinates, 0 repeated codes; 2 points share another
  school's site; 11 without a pupil count (10,649 pupils in the rest); 21 districts, 11 schools in
  Muhanga.
- **To confirm with MINEDUC.** 8 points lie in another district than their record names (codes
  110207, 110327, 110407, 111010, 120117, 130147, 131030, 550713) and 23 in another sector. Kept as
  given: the distance is measured from the point, and which of point or label is wrong is unknown.
  The file's `code_sect_` column is a leftover of an earlier spatial join (it matches 0 of 139
  points) and is not used.

### NCDA ECD Mapping extract

- **Kept 34,448 of 37,431 records**: left out and counted, 2,970 marked not active, 13 with no
  activity status, 1 with no district or sector. No caregiver or child names, no contact details.
- **Types.** `settings_types` mapped to `centre_type`: home_based 25,890, school_based 4,284,
  community_based 2,728, centre_based 832 (centre based, model ECD centre, day-care crèche),
  other 398 (faith-based, market-based, emergency settings, mobile crèches, cross-border,
  prison: no match in the schema), not_stated 316.
- **Identifiers.** `centre_id` is NCDA's `ecd_code`; 192 services without one take
  `NCDA-OBJ-<objectid>`. 0 repeated.
- **Entry errors set to empty, each listed:** 7 enrolments of children aged 3-6 above ten times the
  service's total children (including 16,611 at a service with 170 children) and 1 caregiver
  count of 7,777. Kept as given: 150 services whose 3-6 count exceeds their total by less.
- **Not in the extract, left empty:** capacity and children aged 3-5 (the extract counts ages 3
  to 6). Free places cannot be computed, and the screen says so.
- **Joins.** All 34,448 services join a sector through the crosswalk (61 spell "Shyorongi": one
  reviewed crosswalk row added for NCDA). 915 points lie outside the district they are listed
  in; each keeps its listed sector.
- **Muhanga.** 1,044 active services: 849 home-based, 142 school-based, 27 community-based, 17
  centre-based, 8 not stated, 1 other.

### Census, projections and MINEDUC: verification of the staged tables

- **PHC5 Main Indicators.** Tables 96-100: 416 sectors, 13,246,394 people, every sector
  population **identical** to the staged table. Table 1 (district populations) and Table 58
  (households): largest difference 0. Table 68 (improved drinking water): within 0.1 points
  (rounding).
- **Projections.** Muhanga single ages: population and children aged 3-5 identical to the
  staged table in 10 of 10 years (2026: 365,543 people, 23,931 aged 3-5); single ages add up to
  the total and female + male = both sexes. Each province workbook's total equals the sum of its
  staged districts in all 10 years (50 of 50 province-years).
- **MINEDUC national workbook.** 225 rows, national only, 2020/21 to 2024/25; male + female =
  learners and qualified + unqualified = staff in every year. Against the staged district
  table: schools and classrooms agree in 5 of 5 years; pupils in 4 of 5 (2022/23: districts
  540,962, national 540,998, -36); teachers in 4 of 5 (2021/22: districts 6,347, national 7,351).
  Both gaps were already listed for MINEDUC to confirm.

### WorldPop (blocked: incomplete)

- 9 rasters opened: EPSG:4326, about 93 m cells (3 arc-seconds), no negative values. 2020
  (constrained, UN-adjusted): f_0 154,798, f_1 608,877, m_0 158,622 and f_5 (ages 5-9). 2026
  (R2025A): f_00 195,635, f_01 755,866, m_00 199,634, f_05 and T_Under_18 (all under 18).
- **Missing:** the male ages 1-4 layer in each set (`rwa_m_1_2020_constrained_UNadj.tif`,
  `rwa_m_01_2026_CN_100m_R2025A_v1.tif`). Children under 5 need both sexes; one sex would
  halve the count and skew where children live, and the 2020 and 2026 sets are never mixed. The
  app keeps its census-share stand-in until one set is complete.

### DHS 2025 microdata (stunting, staged as district rates)

- **Pass.** `RWPR91FL.dta` (household-member recode): 57,046 people, survey phase RW8, all
  interviews in 2025, 60 strata, 560 clusters; district code `shdistrict` is the NISR code, so
  all 30 districts join by code.
- **Method (DHS definitions).** De facto children under 5 (`hv103 = 1`) with a valid
  height-for-age z-score (`hc70`); stunted below -2 SD; weighted by `hv005`; 95% intervals by
  Taylor linearisation over strata and clusters. 7,261 children; 10 flagged measurements and 75
  children who did not sleep in the household left out, as the DHS does.
- **Result.** Rwanda 26.8% (95% interval 25.4% to 28.1%); districts from 8.7% (Nyarugenge) to
  38.8% (Gicumbi). Each district rests on 178 to 362 children, so intervals are ±3.9 to ±9.8
  points; the app shows them. Status *model estimate*: IrereroAI's tabulation, to compare with
  the DHS 2025 report before quoting.
- **Kept private.** Only the 30 district rates and intervals are staged and bundled. The other
  10 recode files are not used, and no record is linked across them.

### EICV7 microdata (verification)

- **Pass.** `CS_EICV7_poverty_file.dta`: 15,054 households in 1,674 clusters, 30 districts;
  Rwanda 27.4% below the poverty line (population-weighted `pov_jan`), the published figure.
- **Pass.** All 30 district rates reproduce the staged published rates within 0.05 points.
  Gisagara (45.6%) and Nyamasheke (42.8%), flagged for checking, are confirmed. Muhanga and
  Ruhango (both 15.0% in the chart) are 14.95% and 14.99%; Kamonyi and Nyaruguru are truly equal.
- **Not done, by design.** No sector poverty rate: EICV7 is designed for district estimates.

### OpenStreetMap extract (staged; with the MINEDUC list)

- **Pass.** Geofabrik extract, data as of 29 October 2026 21:21 UTC, written by osmium 1.16.0,
  bounding box inside Rwanda. 12.2 million nodes and 1.7 million ways in the original.
- **Cut to what the app reads.** 174,739 walkable roads and paths (3,803,235 nodes), 577 schools
  and 15 kindergartens: 23 MB of 68 MB. Tags and geometry are kept as mapped; buildings, land
  use and relations are left out.
- **Combined, never double-counted.** The distance layer uses the 592 OSM schools and the 139
  MINEDUC schools; 4 MINEDUC schools lie within 100 m of an OSM school and count once: 727
  schools. Each school on the map says which list it comes from.
- **Walking distance.** Along roads in 407 sectors; 9 sectors where roads reach fewer than half
  the children keep the straight line, labelled indicative. The road graph keeps only roads
  within 1 km of a school, which gives the same distances (checked: 0 of 416 sectors differ from
  the full graph) with peak memory about 1 GB instead of 4.6 GB.
- **Effect.** Nationally 94.1% of children aged 3 to 5 live more than 1 km (walking) from a
  listed school, against 93.9% straight-line from the MINEDUC list alone: more schools, but
  walks are longer than straight lines (Muhanga/Nyamabuye 46% -> 70%). 14 sectors are under 50%.
  Still provisional (OSM marks only 592 schools; MINEDUC counts 4,221 with pre-primary), so it
  stays out of the bottleneck rules: 0 bottlenecks change.

### Reference pages

`Fifth Population and Housing Census  2022.pdf` and `District Profiles  Subnational
projections.pdf` are one-page printouts of NISR web pages (links to reports, no tables): kept as
provenance only.

## What changed in the app's numbers

Built before and after on the same machine; every other table is identical row for row
(observations, the 2026 estimate's counts, the peer model, diagnoses, the 2028/29 forecast).

| Output | Change | Why |
| --- | --- | --- |
| Map shapes and sector areas | 434 of 452 units change area (largest 23 km²); 5 sectors redrawn | NISR 2022 boundaries |
| Sector RW4116 name | Shyrongi -> Shyorongi | Official 2022 spelling |
| Share of children > 1 km from a listed school (provisional) | 85 of 416 sectors change; nationally 93.5% -> 93.9% | 73 sectors from the redrawn shapes; **12 Muhanga sectors** because simulated NCDA centres no longer count as schools (e.g. Cyeza 88.6% -> 100%, Nyamabuye 25.5% -> 46.1%). Before, invented centres lowered real-looking distances |
| NCDA supply table | 36 simulated rows -> 34,448 real services + the 36 labelled demo centres | NCDA extract |
| Stand-ins still used | worldpop, rdhs_2025, ncda -> worldpop only | NCDA extract; DHS 2025 microdata |
| Datasets with real files (Data & methods) | 6 of 10 -> 9 of 10 | Only WorldPop is missing (its male 1-4 layer has not arrived) |
| Share of children > 1 km from a listed school | straight line from 139 MINEDUC schools -> walking distance from 727 OSM and MINEDUC schools; 93.9% -> 94.1% nationally | OpenStreetMap extract |
| Bottleneck diagnosis (DIAGNOSE) | simulated -> model estimate; 37 of 416 sectors change bottleneck (WELLBEING 70 -> 67, SUPPLY 106 -> 109); the 12 Muhanga sectors keep theirs | Real district stunting replaces the stand-in |

## Still missing

| Dataset | What is needed | Effect while missing |
| --- | --- | --- |
| WorldPop | `rwa_m_1_2020_constrained_UNadj.tif` (or `rwa_m_01_2026_CN_100m_R2025A_v1.tif` with the other 2026 layers) | Children are spread evenly inside a sector (documented stand-in) |
| National ECD Standards 2024 | The document, to cite page and wording of each parameter | Parameters stay as configured, cited to the standard without page |
| NCDA ECD Mapping GeoJSON | `ncda_ecd_mapping_extract.geojson` (expected, not uploaded) | None: the CSV carries the coordinates |
| MINEDUC full register | Every school with a pre-primary section, with coordinates | Distance stays an upper bound |

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

## Earlier deliveries (23 to 28 October)

| Package | Files | Publisher, period | Staged | Effect in the app |
| --- | --- | --- | --- | --- |
| EICV7 district poverty | `eicv7_poverty.csv` (and the same table as `.xlsx`) | NISR, EICV7 Main Indicators Report 2023/24, Figure 9.1, p. 80 | **Yes**: `data/raw/eicv7/eicv7_poverty.csv`, 30 districts, status *published estimate* | Poverty in PLAN and DIAGNOSE is now real, at district level, labelled "district" |
| MINEDUC yearbook extracts | 4 district tables (pupils, teachers, classrooms, schools) and 4 national series | MINEDUC, Education Statistical Yearbook 2024/25 (Feb 2026), Annexes 1, 7, 11, 20 and Tables 2.1.2, 2.5.5, 3.4.1, 3.5.1 | Cross-check only: the national series in `data/interim/yearbook/` | Checks the master table below |
| MINEDUC master table | `IrereroAI_MINEDUC_Master_District_Year_2020-21_to_2024-25.csv`: 30 districts × 5 school years, pupils and teachers by sex, schools, classrooms | MINEDUC yearbooks 2021/22 and 2024/25, district annexes | **Yes**: `data/raw/yearbook/mineduc_yearbook_preprimary.csv`, status *observed* | TRACK (the 2028/29 trend and status) and the capacity factor are real |
| MINEDUC validated tables | `irereroai_mineduc_validated_datasets_3.zip`: the same measures, long layout, 2021/22 to 2024/25 | MINEDUC yearbooks 2023/24 and 2024/25 | Cross-check only | Agrees with the master table in every shared cell |
| Census 2022 sector tables | `IrereroAI_Census_2022_Master_Dataset_v1.xlsx`: population, urban share, households, drinking water, lighting and grid connection by sector, with the raw thematic-report tables | NISR, PHC5 2022 thematic reports (Population, Housing): Tables D1, C1.1, C1.2, C1.3, C1.5, 3.2, 3.10 | **Yes**, merged into `data/raw/census_2022/` | The home-environment factor (water) and the peer model's urban, water, electricity and density features |
| MINEDUC school locations | `Rwandapreprimarydata_locatios.GeoJSON`: 139 schools with coordinates | MINEDUC school register | **Yes, provisional**: `data/raw/schools/schools.geojson` (or fetched from the private repository, `IRERERO_SCHOOLS_PATH`) | The distance layer and the Overview school map, labelled provisional; not used in the bottleneck rules |
| COD-AB gazetteer | `rwa_gazetteer_rphc2012_v2.xlsx` | OCHA COD-AB for Rwanda, RPHC 2012 base, via HDX | **Codes only**: `data/reference/pcodes_cod_ab.csv` and both crosswalks | All 416 sectors and 30 districts carry their codes (e.g. Muhanga RW27, Cyeza RW2701) |
| Census 2022 sample records | `children_age_3_5_clean.csv`: 107,238 records of children aged 3 to 5, with sector code, age, attendance and population weight | NISR, PHC5 2022 | **Yes**, as weighted counts: `data/raw/census_2022/`, 416 sectors and 30 district sums, `basis = sample`, status *model estimate* | The 2026 estimate is real: each sector's share of its district's children and its 2022 attendance rate come from the census |
| NISR projections | `nisr_projections_2023_2032.xlsx`: single-age, by sex, 30 districts, 2023 to 2032, with district totals | NISR, Subnational Population Projections 2023-2032 | **Yes**: `data/raw/projections/nisr_projections_2023_2032.csv`, population and children aged 3 to 5 per district and year, status *published estimate* | The 2026 estimate takes each district's children aged 3 to 5 straight from the projection (no 2022 age share held constant) |
| COD-AB boundaries | `provinces/districts/sectors.geojson` (5, 30, 416 units) and a verification report | NISR administrative boundaries via HDX (`rwa_adm_2006_NISR_WGS1984_20181002`) | **Yes**: `data/raw/boundaries/`, codes, names and shapes only | Every map uses the official shapes and NISR codes; provinces keep the app's ids and names (City of Kigali, not Kigali City) |

## What the checks found (earlier deliveries)

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

### MINEDUC school locations (staged, provisional; re-checked on 30 October above)

139 points, all inside Rwanda, all category PRE_PRIMARY (123 private), in 21 districts, with
10,649 pre-primary pupils. MINEDUC counts 4,221 schools with pre-primary and 683,234 pupils in
2024/25: most pre-primary classes are inside primary schools, which this file does not list.

The loader checks every record: 139 of 139 loaded, 0 coordinates outside Rwanda or not
numbers, 0 without a point, 2 sharing another school's coordinates, 11 without a pupil count.
The distance layer uses them with the status **provisional**: the share of children more than
1 km (straight line) from a *listed* school is an upper bound (≤ 94% nationally; 17 sectors
under 50%), shown with that label on the Overview, the sector page and Data & methods. It is
not used as evidence in the bottleneck rules or the access score, and a sector far from a
listed school is never read as having no school. Still needed: the full school list with
coordinates and a flag for schools with pre-primary classes.

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

### COD-AB boundaries (replaced on 30 October by the NISR 2022 sector layer)

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

`make data` reports a simulated stand-in for **worldpop** only, the school list as provisional, and the NCDA extract as real (with the 36 Muhanga LEARN demonstration centres
beside it in demo mode, labelled SIMULATED).

| Part of the app | Status now | Why |
| --- | --- | --- |
| Maps, sector filters and every spatial join | **observed** | NISR 2022 sector layer |
| Children aged 3 to 5 in 2026, attending, places, rooms (PLAN) | **model estimate** | Census sample, NISR projections |
| Priority ranking (PLAN) | **model estimate** | Estimate, peer gap, EICV7 poverty (district) |
| Peer benchmark (DIAGNOSE) | **model estimate** | Census attendance and household tables |
| 2028/29 trend and status (TRACK) | **model estimate** on **observed** yearbooks | MINEDUC district table, checked against the national workbook |
| Share of children more than 1 km from a school | **provisional** (upper bound) | 139 standalone pre-primary schools; no simulated centres |
| Bottlenecks and factor scores (DIAGNOSE) | **model estimate** | DHS 2025 district stunting (microdata), with the other factors |
| NCDA connector (Data & methods) | **observed**, hidden by default | Shown only when `IRERERO_NCDA_DISPLAY` is on |
| LEARN check-ins and course progress | simulated (demo mode) | No real operational records yet |

**Attendance in 2026, a stated choice (unchanged).** The census 2022 rate is used
(`MINEDUC_TREND_ON_CENSUS` is off): with the real yearbooks, moving it by MINEDUC growth puts 250
of 416 sectors at the 98% cap. TRACK shows MINEDUC's own gross rate (65.3% nationally in 2024/25).

**Read TRACK with care (unchanged).** The straight-line trend runs through the 2022/23 jump (+52%
pupils), so it is steep and reaches the 100% cap in many districts; the back-test error is 5.1
points. The gross rate counts over-age pupils.
