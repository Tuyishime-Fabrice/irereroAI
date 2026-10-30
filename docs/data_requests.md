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
| 7 | [School list with coordinates](#7-openstreetmap-rwanda) (every school with pre-primary classes) | MINEDUC (EMIS), or OpenStreetMap | Ask; or open download | The 1 km distance, the access factor and most bottlenecks | **1, essential** |
| 4 | [Stunting by district](#4-stunting-under-5-by-district) (`Microdata (1).zip` expected, not yet uploaded) | NISR, MoH, DHS Program | Published report; microdata under DHS terms | The wellbeing factor; the nutrition course trigger; with schools, a real diagnosis | **1, essential** |
| 3 | [Qualified teachers by district](#3-mineduc-yearbooks) | MINEDUC | Ask | The third part of the capacity factor | 2 |
| 1 | [Census sanitation, women's education, children 0-4 by sector; Table 2.5 totals](#1-census-2022-phc5-sector-tables) | NISR | Thematic reports; ask | The rest of the home-environment factor; a check of the sample counts | 2 |
| 6 | [WorldPop: the male 1-4 layer](#6-worldpop-under-5-2020) (the rest arrived on 30 Oct) | WorldPop | Open download | Where children live inside a sector; the distance layer | 2 |
| 2 | [Projection variants](#2-population-projections-2023-2032) | NISR | Published; ask | Low and high variants for the 2026 range | 3 |
| 8 | [NCDA: confirm the data-sharing terms](#8-ncda-ecd-mapping-system-extract) (extract received 30 Oct) | NCDA | Data sharing agreement | Showing the services on screen (`IRERERO_NCDA_DISPLAY`) | 3 |
| 9 | [EICV7 sector rates and two checks](#9-eicv7-follow-up) (`Microdata.zip` expected, not yet uploaded) | NISR | Published; microdata under NISR terms | Poverty that separates sectors inside a district | 3 |
| 10 | National ECD Standards 2024 document | NCDA | Published | Page and wording for the 30 per room, 1:15-1:30 and 1 km parameters | 3 |

Received and in use: the census 2022 children aged 3 to 5 (sample records) and sector tables,
the NISR single-age projections, the MINEDUC yearbooks 2020/21 to 2024/25, the COD-AB boundaries
and the EICV7 district poverty table (see [data_inventory.md](data_inventory.md)). PLAN and
TRACK are real. What still carries the red SIMULATED label: the bottleneck diagnosis, until stunting arrives.
The share of children more than 1 km from a school is PROVISIONAL (an upper bound from the 139
standalone pre-primary schools) until the full school list arrives.

## 1. Census 2022 (PHC5) sector tables

**Received:** the attendance counts (sample records) and, by sector, population, urban share,
households, drinking water and grid connection (thematic-report tables). Still wanted:

- **By sector:** households with improved sanitation, women aged 15+ with secondary education or
  more (Education thematic report), and children aged 0 to 4. These complete the
  home-environment factor, which now rests on water alone.
- **The printed Table 2.5 district totals** (children aged 3 to 5 attending and never attended),
  to check the counts weighted from the sample records.
- **Where:** https://www.statistics.gov.rw/publication/2093 and the PHC5 thematic reports

## 2. Population projections 2023-2032

**Received:** single-age projections by district, 2023 to 2032, one variant (read as the
medium one). Still wanted: the **low and high variants**, if NISR publishes them, so the 2026
range reflects projection uncertainty instead of a default error. Template:
`nisr_projections_2023_2032.csv` (`population_low`, `population_high`).

## 3. MINEDUC yearbooks

**Received:** the master table, 30 districts × 2020/21 to 2024/25 (pupils and teachers by sex,
schools, classrooms), in use. Still wanted:

- **Qualified teachers by district** for each year (only the national share is published:
  99.4% in 2024/25).
- **Confirm with MINEDUC:** Nyarugenge pupils 2023/24 (12,893 printed, 12,863 by sex), the eight
  Southern teacher totals 2023/24 (each 10 below men + women), 2022/23 district pupils (36 short
  of the national total) and 2021/22 teachers (6,347 by district vs 7,351 national).
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

**Received 30 October:** f_0, f_1, m_0 (2020) and f_00, f_01, m_00 (2026, R2025A), plus age 5-9
and under-18 layers the app does not use. **Still missing:** `rwa_m_1_2020_constrained_UNadj.tif`
(or, for the 2026 set, `rwa_m_01_2026_CN_100m_R2025A_v1.tif`). The two sets are never mixed.

- **Download:** WorldPop age and sex structures, constrained, 100 m, 2020, UN adjusted, for
  Rwanda: the four files for females and males aged 0 and 1 to 4
  (`rwa_f_0_2020_constrained_UNadj.tif`, `rwa_f_1_…`, `rwa_m_0_…`, `rwa_m_1_…`).
- **Where:** https://hub.worldpop.org/project/categories?id=8 (CC BY 4.0)

## 7. OpenStreetMap Rwanda

- **Best:** the MINEDUC school list with coordinates for **every** school with pre-primary
  classes (most are primary schools with a pre-primary section), with a pre-primary flag. The
  list received on 28 October holds only the 139 standalone pre-primary schools: it is in use,
  labelled provisional, but it is not enough. Ask MINEDUC's EMIS team for the full register,
  then replace the file at the same path (`IRERERO_SCHOOLS_PATH`).
- **Or download:** `rwanda-latest.osm.pbf` into `data/raw/osm/`, and install the road extra
  with `uv sync --extra osm`. OSM does not mark which schools have pre-primary.
- Either one makes the 1 km distance, the access factor and most bottlenecks real.
- **Where:** https://download.geofabrik.de/africa/rwanda.html (ODbL 1.0)

## 8. NCDA ECD Mapping System extract

**Received 30 October** (`ncda_ecd_mapping_extract.csv`, 37,431 records; 34,448 active
services staged). Still to settle: whether the data-sharing agreement allows the services to be
shown publicly, and, ideally, each centre's capacity and enrolment aged 3 to 5. The expected
GeoJSON copy was not uploaded (the CSV carries the coordinates).

- **Originally asked for:** an extract in the `supply_extract` schema (one row per centre: id, name, type,
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
