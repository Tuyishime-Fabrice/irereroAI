# Datasets still needed

What IrereroAI still runs on simulated stand-ins, what exactly to ask for, and where. Each item
names the screens it unlocks, the table to look for, the columns the loader reads, and a
header-only template in [`data/templates/`](../data/templates/) (generated from the loaders,
so it always matches). Full column definitions are in [DATA_SOURCES.md](../DATA_SOURCES.md).
What has already been received is in [data_inventory.md](data_inventory.md).

Received files go in through `make intake FILES="<file or folder>"` (tables in their own
layout) or straight into `data/raw/<dataset>/` (tables typed into the template), then
`make data`.

## Priority

| # | Dataset | From | Access | Unlocks | Priority |
| --- | --- | --- | --- | --- | --- |
| 3 | [MINEDUC yearbooks, earlier years and qualified teachers](#3-mineduc-yearbooks) | MINEDUC | Published PDFs | The 2029 trend and status; attendance moved since 2022; the capacity factor | **1, essential** |
| 7 | [OpenStreetMap extract](#7-openstreetmap-rwanda) (or a MINEDUC school list with coordinates) | Geofabrik, MINEDUC | Open download | Real school points: the 1 km distance, the access factor and most bottlenecks | **1, essential** |
| 4 | [Stunting by district](#4-stunting-under-5-by-district) | NISR, MoH, DHS Program | Published report | The wellbeing factor; the nutrition course trigger | 2 |
| 1 | [Census 2022 sector tables, the other columns](#1-census-2022-phc5-sector-tables) | NISR | Published PDFs; ask for CSV | The home-environment factor and richer peer model; a check of the sample counts | 2 |
| 6 | [WorldPop under-5 rasters](#6-worldpop-under-5-2020) | WorldPop | Open download | Where children live inside a sector; the distance layer | 2 |
| 2 | [Projection variants](#2-population-projections-2023-2032) | NISR | Published; ask | Low and high variants for the 2026 range | 3 |
| 8 | [NCDA ECD Mapping extract](#8-ncda-ecd-mapping-system-extract) | NCDA | Data sharing agreement | Real centres for LEARN and the supply connector | 3 |
| 9 | [EICV7 sector rates and two checks](#9-eicv7-follow-up) | NISR | Published; ask | Poverty that separates sectors inside a district | 3 |
| 5 | ~~COD-AB boundary files~~ | NISR via HDX | Received 24 Oct 2026 | Official shapes and codes on every map | done |

Received and in use: the census 2022 children aged 3 to 5 (sample records, weighted to sector
counts), the NISR single-age projections, the COD-AB boundaries and the EICV7 district
poverty table (see [data_inventory.md](data_inventory.md)). The 2026 estimate, the priority
ranking and the peer benchmark are now real. What still carries the red SIMULATED label: the
2028/29 trend (yearbook), the share of children more than 1 km from a school (school points)
and the bottleneck diagnosis (yearbook, stunting, school points).

## 1. Census 2022 (PHC5) sector tables

**Received in part.** The sample records of children aged 3 to 5 give attending and never
attended per sector (as weighted counts). Still wanted:

- **Ask for:** by sector, from the 30 district profiles or as CSV: resident population,
  children aged 0 to 4, private households, households with improved water, improved
  sanitation and electricity, share urban, and women aged 15+ with secondary education or
  more. These feed the home-environment factor (now "no data") and the peer model.
- **Also:** the printed **Table 2.5 district totals** (children aged 3 to 5 attending and never
  attended), to check the sample counts against the full count. With the full Table 2.5 by
  sector, the counts become *observed* instead of a model estimate.
- **Templates:** `census_2022_sectors.csv` (sector rows), `census_2022_districts.csv`.
- **Where:** https://www.statistics.gov.rw/publication/2093

## 2. Population projections 2023-2032

**Received:** single-age projections by district, 2023 to 2032, one variant (read as the
medium one). Still wanted: the **low and high variants**, if NISR publishes them, so the 2026
range reflects projection uncertainty instead of a default error. Template:
`nisr_projections_2023_2032.csv` (`population_low`, `population_high`).

## 3. MINEDUC yearbooks

The 2024/25 extract is received but cannot stand in yet. Still needed, by district, for
pre-primary:

| School year | Pupils | Schools | Classrooms | Teachers | Qualified teachers |
| --- | --- | --- | --- | --- | --- |
| 2020/21 | needed | needed | needed | needed | needed |
| 2021/22 | needed | needed | needed | needed | needed |
| 2022/23 | needed | received | received | needed | needed |
| 2023/24 | received* | received | received | received* | needed |
| 2024/25 | received | received | received | received | needed |

\* to confirm against the PDF: Nyarugenge pupils 2023/24 (12,893 or 12,863) and the Southern
teacher totals 2023/24 (each 10 below male + female). Details in
[data_inventory.md](data_inventory.md#mineduc-yearbook-not-staged).

- **Ask for / look in:** the Education Statistical Yearbooks 2020/21, 2021/22 and 2022/23 (and
  2023/24 for qualified teachers), district annex tables for pre-primary pupils, schools,
  classrooms, teachers and **qualified teachers**.
- **Format:** the same layout as the extracts received (`preprimary_<measure>_by_district.csv`
  with `<measure>_<YYYY>_<YY>` columns) through `make intake`, which merges the years and
  stages the table once it is complete; or the template `mineduc_yearbook_preprimary.csv`.
- **Where:** https://www.mineduc.gov.rw

## 4. Stunting under 5 by district

- **Ask for:** the latest Rwanda Demographic and Health Survey (the round the app labels
  "RDHS 2025"): **stunting, children under 5, by district**, with the 95% confidence interval.
  Confirm the survey round and table number when the report is in hand, and update the
  dataset title if it differs.
- **Template:** `rdhs_2025_stunting.csv`. Required: `district_name`, `stunting_u5` (write 38.8%
  as 0.388).
- **Where:** https://www.statistics.gov.rw and https://dhsprogram.com

## 5. Official boundaries (COD-AB)

**Received** on 24 October 2026 and in use (5 provinces, 30 districts, 416 sectors). Before a
production release, confirm with NISR that the 2006 administrative structure in the file is
current.

## 6. WorldPop under 5, 2020

- **Download:** WorldPop age and sex structures, constrained, 100 m, 2020, UN adjusted, for
  Rwanda: the four files for females and males aged 0 and 1 to 4
  (`rwa_f_0_2020_constrained_UNadj.tif`, `rwa_f_1_…`, `rwa_m_0_…`, `rwa_m_1_…`).
- **Where:** https://hub.worldpop.org/project/categories?id=8 (CC BY 4.0)

## 7. OpenStreetMap Rwanda

- **Download:** `rwanda-latest.osm.pbf` into `data/raw/osm/`, and install the road extra
  with `uv sync --extra osm`. OSM does not mark which schools have pre-primary, so a MINEDUC
  school list with coordinates and a pre-primary flag (ask MINEDUC's EMIS team) would be a
  better source. Either one makes the 1 km distance, the access factor and most bottlenecks
  real.
- **Where:** https://download.geofabrik.de/africa/rwanda.html (ODbL 1.0)

## 8. NCDA ECD Mapping System extract

- **Ask for:** an extract in the `supply_extract` schema (one row per centre: id, name, type,
  district, sector, longitude, latitude, capacity, children aged 3 to 5 enrolled, caregivers,
  date), starting with Muhanga for the LEARN pilot. Centre-level counts only, no child records.
- **Template:** `supply_extract.csv`. Needs a data sharing agreement with NCDA.

## 9. EICV7 follow-up

- **Confirm** the Gisagara and Nyamasheke rates: the received chart reading and the report
  text disagree.
- **Ask whether** sector-level poverty from EICV7 (or a small-area estimate) can be shared.
  With it, poverty separates sectors inside a district again.
- **Template:** `eicv7_poverty.csv`, `level = sector` rows with `sector_name`.

## Request note (draft)

A short note the team can adapt for NISR or MINEDUC. Fill in the names and the list.

> Subject: Request for published pre-primary and population tables, IrereroAI (NISR 2026 Big
> Data Hackathon, Track 3)
>
> Dear [name],
>
> Our team is building IrereroAI, a planning tool that helps district planners see where
> pre-primary places are needed and whether districts are on track for the NST2 target of 65%
> enrolment by 2028/29. It uses published aggregates only, at district and sector level; it
> holds no microdata or personal records.
>
> We would be grateful for the following tables in CSV or Excel, where they exist: [list the
> items above, e.g. "Census 2022 Table 2.5 by sector, for all 30 districts"].
>
> We keep the files off public repositories, record a checksum of each file, cite [NISR /
> MINEDUC] and the table on every figure, show counts below 10 as "fewer than 10", and will
> delete the files on request.
>
> Kind regards,
> [name, role, team, contact]
