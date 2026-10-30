# Data sources

Generated from the declarations in `irerero/data/` by `python -m irerero.data --write`; do not edit by hand.

Put each file in its folder under `data/raw/` and run `make data`. Raw files never enter git. When a file is missing, the committed demo bundle in `data/demo/` stands in and every value from it carries the red SIMULATED badge and is left out of exports. When a file is present but does not match its columns, `make data` stops and names the file, line and column to fix.

Every name joins to the NISR sector code through the reviewed crosswalks `data/reference/sector_name_crosswalk.csv` and `district_name_crosswalk.csv`. There is no fuzzy matching at run time: if a source spells a sector differently, add a row for that source to the crosswalk.

```
data/
  raw/            your files, one folder per dataset (gitignored)
  interim/        parsed intermediates, e.g. census tables from the PDFs (gitignored)
  processed/      Parquet and simplified GeoJSON written by make data (gitignored)
  reference/      reviewed crosswalks (committed)
  demo/           simulated stand-ins and geoBoundaries shapes (committed)
```

| # | Dataset | Level | Period | Used by |
| --- | --- | --- | --- | --- |
| 1 | [Fifth Population and Housing Census (PHC5) 2022, district profiles](#census_2022) | sector, with district totals for checking | 2022 (census night 15 August 2022) | PLAN: 2026 estimate, gap, priority; DIAGNOSE: home environment, peer model |
| 2 | [WorldPop age and sex structures, constrained, 100 m, 2020 (UN adjusted)](#worldpop) | 100 m grid | 2020 | PLAN: where children live inside each sector (2026 estimate, distance layer) |
| 3 | [Rwanda Subnational Population Projections 2023-2032](#projections) | district | 2023 to 2032 | PLAN: calibrate the 2026 estimate; TRACK: population for enrolment rates |
| 4 | [Administrative boundaries, province to sector (NISR 2022)](#boundaries) | province, district, sector | 2022 | every map; the join to NISR sector codes |
| 5 | [OpenStreetMap Rwanda extract](#osm) | points and road network | extract date | PLAN: share of children more than 1 km from a school with pre-primary |
| 6 | [MINEDUC school locations (provisional: standalone pre-primary schools only)](#schools) | school points | register export (date not stated) | PLAN: share of children more than 1 km from a listed school (provisional upper bound); Overview map: school locations |
| 7 | [Education Statistical Yearbooks 2020/21 to 2024/25 (pre-primary)](#yearbook) | district | 2020/21 to 2024/25 | TRACK: enrolment trend to 2029; DIAGNOSE: capacity (ratios, qualifications) |
| 8 | [Rwanda Demographic and Health Survey 2025](#rdhs_2025) | district | 2025 | DIAGNOSE: wellbeing (district context); LEARN: nutrition course trigger |
| 9 | [Integrated Household Living Conditions Survey 7 (EICV7), 2023/24](#eicv7) | sector if published, otherwise district | 2023/24 | PLAN: poverty component of the priority index; DIAGNOSE: poverty factor |
| 10 | [National ECD Standards (2024)](#ecd_standards) | national | 2024 | PLAN: 30 children per room, 1 caregiver per 15 to 30 children, 1 km walk |
| 11 | [Course source materials (NCDA, UNICEF, WHO)](#courses) | course | as cited | LEARN: the four courses |
| 12 | [NCDA ECD Mapping System extract (supply_extract schema)](#ncda) | centre | as_of date | LEARN: centres and caregivers in the pilot; Data and methods: optional supply connector (off by default) |
| 13 | [Simulated check-ins and course progress, Muhanga](#learn_simulation) | centre | 2026 | LEARN: demo caregivers, check-ins, triggers and progress |

<a id="census_2022"></a>

## 1. Fifth Population and Housing Census (PHC5) 2022, district profiles

| | |
| --- | --- |
| Publisher | NISR |
| Folder | `data/raw/census_2022/` |
| Expected files | `census_2022_sectors.csv`, `census_2022_districts.csv` |
| Format | CSV (or the 30 district profile PDFs, parsed into these two CSVs) |
| Geographic level | sector, with district totals for checking |
| Reference period | 2022 (census night 15 August 2022) |
| Licence | NISR publication; cite NISR PHC5 2022 |
| Where to get it | https://www.statistics.gov.rw/publication/2093 |
| Status when loaded | observed |
| Used by | PLAN: 2026 estimate, gap, priority; DIAGNOSE: home environment, peer model |
| While missing | Simulated sector table for all 416 sectors (seed 2026) |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `sector_name` | text | yes | Sector name as printed in the source |
| `district_name` | text | yes | District name as printed in the source |
| `children_3_5` | whole number ≥ 0 | yes | Children aged 3 to 5 (Table 2.5 total) |
| `children_3_5_attending` | whole number ≥ 0 | yes | Of them, attending nursery school (Table 2.5) |
| `children_3_5_never_attended` | whole number ≥ 0 | yes | Of them, never attended (Table 2.5) |
| `population` | whole number ≥ 0 | no | Resident population |
| `children_0_4` | whole number ≥ 0 | no | Children aged 0 to 4 |
| `households` | whole number ≥ 0 | no | Private households |
| `hh_improved_water` | whole number ≥ 0 | no | Households using an improved water source |
| `hh_improved_sanitation` | whole number ≥ 0 | no | Households with improved sanitation |
| `hh_electricity` | whole number ≥ 0 | no | Households with electricity |
| `urban_share` | share, 0 to 1 | no | Share of the population living in urban areas |
| `women_secondary_share` | share, 0 to 1 | no | Women aged 15+ with secondary education or more (proxy for mothers' education) |
| `basis` | text | no | 'table' (printed Table 2.5, the default) or 'sample' (weighted from census sample records by `make intake`) |
| `source_page` | text | no | Page or table the value was read from |

Put the 30 district profile PDFs in data/raw/census_2022/pdf/ and run `make data`: Table 2.5 and the other tables are parsed into the two CSVs in data/interim/. Or type the CSVs directly into data/raw/census_2022/.

census_2022_districts.csv holds the district total rows printed in each profile, so the build can check that sector rows add up.

Census sample records of children aged 3 to 5 (with population weights) can stand in for Table 2.5: `make intake` weights them to sector counts and marks them basis = sample, which makes their status a model estimate.

<a id="worldpop"></a>

## 2. WorldPop age and sex structures, constrained, 100 m, 2020 (UN adjusted)

| | |
| --- | --- |
| Publisher | WorldPop, University of Southampton |
| Folder | `data/raw/worldpop/` |
| Expected files | `rwa_f_0_2020_constrained_UNadj.tif`, `rwa_f_1_2020_constrained_UNadj.tif`, `rwa_m_0_2020_constrained_UNadj.tif`, `rwa_m_1_2020_constrained_UNadj.tif` |
| Format | GeoTIFF, EPSG:4326 |
| Geographic level | 100 m grid |
| Reference period | 2020 |
| Licence | CC BY 4.0 |
| Where to get it | https://hub.worldpop.org/project/categories?id=8 |
| Status when loaded | published estimate |
| Used by | PLAN: where children live inside each sector (2026 estimate, distance layer) |
| While missing | Sector shares of the census 3-5 count; the distance layer spreads children evenly |

Age group 0 is under 1 and group 1 is 1 to 4; both sexes are summed.

<a id="projections"></a>

## 3. Rwanda Subnational Population Projections 2023-2032

| | |
| --- | --- |
| Publisher | NISR |
| Folder | `data/raw/projections/` |
| Expected files | `nisr_projections_2023_2032.csv` |
| Format | CSV typed from the published tables |
| Geographic level | district |
| Reference period | 2023 to 2032 |
| Licence | NISR publication; cite NISR |
| Where to get it | https://www.statistics.gov.rw |
| Status when loaded | published estimate |
| Used by | PLAN: calibrate the 2026 estimate; TRACK: population for enrolment rates |
| While missing | Simulated district projections (seed 2026) |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `district_name` | text | yes | District name as printed in the source |
| `year` | whole number ≥ 0 | yes | Projection year |
| `population` | whole number ≥ 0 | yes | Projected population, medium variant |
| `population_low` | whole number ≥ 0 | no | Low variant |
| `population_high` | whole number ≥ 0 | no | High variant |
| `children_3_5` | whole number ≥ 0 | no | Projected children aged 3 to 5 (from the single-age tables), medium variant |
| `source_page` | text | no | Page or table the value was read from |

With children_3_5 (the single-age tables give it), the 2026 estimate takes each district's children aged 3 to 5 straight from the projection; without it, from the projected population and the census 2022 age share.

<a id="boundaries"></a>

## 4. Administrative boundaries, province to sector (NISR 2022)

| | |
| --- | --- |
| Publisher | NISR via the Humanitarian Data Exchange |
| Folder | `data/raw/boundaries/` |
| Expected files | `provinces.geojson`, `districts.geojson`, `sectors.geojson` |
| Format | GeoJSON, EPSG:4326 |
| Geographic level | province, district, sector |
| Reference period | 2022 |
| Licence | CC BY 4.0 as declared for COD-AB on HDX; confirm the terms of the 2022 sector layer |
| Where to get it | https://data.humdata.org/dataset/cod-ab-rwa |
| Status when loaded | observed |
| Used by | every map; the join to NISR sector codes |
| While missing | geoBoundaries gbOpen RWA (CC BY 4.0, from NISR open data), simplified; real shapes, no NISR codes |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `nisr_code` | text | yes | Official NISR code of the unit |
| `name` | text | yes | Official name |
| `parent_nisr_code` | text | no | NISR code of the unit one level up |

Rename the COD-AB columns to nisr_code, name and parent_nisr_code. Each nisr_code must be in the reviewed crosswalks (nisr_sector_code, nisr_district_code).

Or put the NISR 2022 sector layer (Rwanda_Sector_Boundaries_2022.geojson, with province_id, district_id and sector_id) through `make intake`: it writes the three files, districts and provinces as the union of their sectors.

<a id="osm"></a>

## 5. OpenStreetMap Rwanda extract

| | |
| --- | --- |
| Publisher | OpenStreetMap contributors, via Geofabrik |
| Folder | `data/raw/osm/` |
| Expected files | `rwanda-latest.osm.pbf` |
| Format | OSM PBF |
| Geographic level | points and road network |
| Reference period | extract date |
| Licence | ODbL 1.0 |
| Where to get it | https://download.geofabrik.de/africa/rwanda.html |
| Status when loaded | observed |
| Used by | PLAN: share of children more than 1 km from a school with pre-primary |
| While missing | Simulated school points; straight-line distance, labelled indicative |

Schools are amenity=school or amenity=kindergarten. Most Rwandan primary schools host pre-primary, but OSM does not say which: treat the layer as an approximation.

Needs `uv sync --extra osm` (pyosmium and networkx). Without it, or where roads are thin, distance is straight-line and labelled indicative.

<a id="schools"></a>

## 6. MINEDUC school locations (provisional: standalone pre-primary schools only)

| | |
| --- | --- |
| Publisher | Ministry of Education (MINEDUC), school register |
| Folder | `data/raw/schools/` |
| Expected files | `schools.geojson` |
| Format | GeoJSON points, EPSG:4326 (the register's export) |
| Geographic level | school points |
| Reference period | register export (date not stated) |
| Licence | MINEDUC data; cite MINEDUC |
| Where to get it | not public |
| Status when loaded | provisional |
| Used by | PLAN: share of children more than 1 km from a listed school (provisional upper bound); Overview map: school locations |
| While missing | Simulated school points (or OpenStreetMap when its extract is loaded) |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `school_code` | text | yes | MINEDUC school code |
| `school_name` | text | no | School name |
| `district` | text | no | District |
| `sector` | text | no | Sector |
| `school_category` | text | no | Category (PRE_PRIMARY in this copy) |
| `preprimary_students_total` | whole number ≥ 0 | no | Pre-primary pupils |

Fetched from the team's private repository on first start when IRERERO_SCHOOLS_PATH is set (see docs/deploy_private_data.md), or put in data/raw/schools/schools.geojson.

Partial list: the distance results are provisional and are not used as evidence in the bottleneck rules.

<a id="yearbook"></a>

## 7. Education Statistical Yearbooks 2020/21 to 2024/25 (pre-primary)

| | |
| --- | --- |
| Publisher | Ministry of Education (MINEDUC) |
| Folder | `data/raw/yearbook/` |
| Expected files | `mineduc_yearbook_preprimary.csv` |
| Format | CSV typed from the yearbook district tables |
| Geographic level | district |
| Reference period | 2020/21 to 2024/25 |
| Licence | MINEDUC publication; cite the yearbook and year |
| Where to get it | https://www.mineduc.gov.rw |
| Status when loaded | observed |
| Used by | TRACK: enrolment trend to 2029; DIAGNOSE: capacity (ratios, qualifications) |
| While missing | Simulated district series (seed 2026) |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `district_name` | text | yes | District name as printed in the source |
| `school_year` | text | yes | 2020/21 ... 2024/25 |
| `pupils` | whole number ≥ 0 | yes | Pre-primary pupils |
| `schools` | whole number ≥ 0 | yes | Schools with pre-primary |
| `classrooms` | whole number ≥ 0 | yes | Pre-primary classrooms |
| `teachers` | whole number ≥ 0 | yes | Pre-primary teachers |
| `qualified_teachers` | whole number ≥ 0 | no | Of them, qualified (not published by district so far; capacity then uses the ratios only) |
| `source_page` | text | no | Page or table the value was read from |

<a id="rdhs_2025"></a>

## 8. Rwanda Demographic and Health Survey 2025

| | |
| --- | --- |
| Publisher | NISR, Ministry of Health, The DHS Program |
| Folder | `data/raw/rdhs_2025/` |
| Expected files | `rdhs_2025_stunting.csv` |
| Format | CSV typed from the report table |
| Geographic level | district |
| Reference period | 2025 |
| Licence | Published report; cite NISR and The DHS Program |
| Where to get it | https://www.statistics.gov.rw |
| Status when loaded | published estimate |
| Used by | DIAGNOSE: wellbeing (district context); LEARN: nutrition course trigger |
| While missing | Simulated district values (seed 2026) |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `district_name` | text | yes | District name as printed in the source |
| `stunting_u5` | share, 0 to 1 | yes | Children under 5 below -2 SD height-for-age |
| `stunting_u5_low` | share, 0 to 1 | no | Lower 95% bound |
| `stunting_u5_high` | share, 0 to 1 | no | Upper 95% bound |
| `source_page` | text | no | Page or table the value was read from |

Write 38.8% as 0.388.

<a id="eicv7"></a>

## 9. Integrated Household Living Conditions Survey 7 (EICV7), 2023/24

| | |
| --- | --- |
| Publisher | NISR |
| Folder | `data/raw/eicv7/` |
| Expected files | `eicv7_poverty.csv` |
| Format | CSV typed from the district presentations |
| Geographic level | sector if published, otherwise district |
| Reference period | 2023/24 |
| Licence | NISR publication; cite NISR EICV7 |
| Where to get it | https://www.statistics.gov.rw |
| Status when loaded | published estimate |
| Used by | PLAN: poverty component of the priority index; DIAGNOSE: poverty factor |
| While missing | Simulated sector values (seed 2026) |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `level` | text | yes | sector or district |
| `district_name` | text | yes | District name as printed |
| `sector_name` | text | no | Sector name, for sector rows |
| `poverty_rate` | share, 0 to 1 | yes | Share of people below the national poverty line |
| `source_page` | text | no | Page or table the value was read from |

<a id="ecd_standards"></a>

## 10. National ECD Standards (2024)

| | |
| --- | --- |
| Publisher | National Child Development Agency (NCDA) |
| Folder | none |
| Expected files | none |
| Format | Parameters in irerero/config.py, each cited |
| Geographic level | national |
| Reference period | 2024 |
| Licence | Government publication; cited |
| Where to get it | https://www.ncda.gov.rw |
| Status when loaded | published estimate |
| Used by | PLAN: 30 children per room, 1 caregiver per 15 to 30 children, 1 km walk |
| While missing | Not a file: the parameters are always present |

<a id="courses"></a>

## 11. Course source materials (NCDA, UNICEF, WHO)

| | |
| --- | --- |
| Publisher | NCDA, UNICEF, WHO |
| Folder | none |
| Expected files | none |
| Format | Markdown lessons and JSON quizzes in content/courses/, each citing its source |
| Geographic level | course |
| Reference period | as cited |
| Licence | Adapted from public materials, cited in each course |
| Where to get it | not public |
| Status when loaded | observed |
| Used by | LEARN: the four courses |
| While missing | Lesson text is marked placeholder until the team finalises it |

<a id="ncda"></a>

## 12. NCDA ECD Mapping System extract (supply_extract schema)

| | |
| --- | --- |
| Publisher | National Child Development Agency (NCDA) |
| Folder | `data/raw/ncda/` |
| Expected files | `supply_extract.csv` |
| Format | CSV in the supply_extract schema |
| Geographic level | centre |
| Reference period | as_of date |
| Licence | NCDA data sharing agreement |
| Where to get it | not public |
| Status when loaded | observed |
| Used by | LEARN: centres and caregivers in the pilot; Data and methods: optional supply connector (off by default) |
| While missing | Simulated Muhanga extract (seed 2026) |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `centre_id` | text | yes | NCDA centre id |
| `name` | text | yes | Centre name |
| `centre_type` | text | yes | home_based | community_based | school_based | centre_based | other | not_stated |
| `sector_name` | text | yes | Sector name as printed in the source |
| `district_name` | text | yes | District name as printed in the source |
| `lon` | longitude, WGS84 (28.7 to 31.0) | yes | Longitude (WGS84) |
| `lat` | latitude, WGS84 (-2.95 to -1.0) | yes | Latitude (WGS84) |
| `capacity` | whole number ≥ 0 | no | Places (not in the NCDA extract) |
| `enrolled_3_5` | whole number ≥ 0 | no | Children aged 3 to 5 enrolled |
| `enrolled_3_6` | whole number ≥ 0 | no | Children aged 3 to 6 enrolled (NCDA) |
| `caregivers` | whole number ≥ 0 | no | Caregivers |
| `as_of` | YYYY-MM-DD | yes | Date of the record, YYYY-MM-DD |

Never added to census or MINEDUC enrolment: NCDA counts include home-based ECD, the formal pre-primary measure does not.

Put ncda_ecd_mapping_extract.csv through `make intake`: it keeps active services, maps settings_types to centre_type and writes this file. Rows are shown on screen only when IRERERO_NCDA_DISPLAY is on (the data-sharing agreement must allow it).

<a id="learn_simulation"></a>

## 13. Simulated check-ins and course progress, Muhanga

| | |
| --- | --- |
| Publisher | IrereroAI demo generator (seed 2026) |
| Folder | none |
| Expected files | none |
| Format | Generated at first start into the app tables |
| Geographic level | centre |
| Reference period | 2026 |
| Licence | Simulated; no real people |
| Where to get it | not public |
| Status when loaded | simulated |
| Used by | LEARN: demo caregivers, check-ins, triggers and progress |
| While missing | Always simulated: plants no water, few meal days and an attendance drop |
