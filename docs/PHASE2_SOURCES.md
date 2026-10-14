# Phase 2 sources

Generated from the adapter specs by `python -m pipelines.registry --write`; do not edit.
How to implement an adapter is in [PHASE2_HANDOFF.md](PHASE2_HANDOFF.md).

| Adapter | Source | Origin | Target tables |
| --- | --- | --- | --- |
| [`census_2022`](#census_2022) | Fifth Rwanda Population and Housing Census (PHC5), 2022 | official | `area_indicator` |
| [`eicv7`](#eicv7) | Integrated Household Living Conditions Survey 7 (EICV7) | official | `area_indicator` |
| [`rdhs_2025`](#rdhs_2025) | Rwanda Demographic and Health Survey 2025 | official | `area_indicator` |
| [`rdhs_2019_gps`](#rdhs_2019_gps) | Rwanda DHS 2019-20 cluster locations | official | `area_indicator` |
| [`lfs_2025`](#lfs_2025) | Labour Force Survey 2025 | official | `area_indicator` |
| [`education_yearbook`](#education_yearbook) | Education Statistical Yearbook | official | `area_indicator`, `candidate_site` |
| [`ncda_mapping`](#ncda_mapping) | NCDA ECD Mapping System and digitised ECD book | partner | `centre`, `weekly_report` |
| [`worldpop`](#worldpop) | WorldPop age and sex structures, constrained, 100 m | public | `area_indicator` |
| [`osm`](#osm) | OpenStreetMap Rwanda extract | public | `area_indicator`, `candidate_site` |
| [`boundaries`](#boundaries) | Official administrative boundaries, province to village | official | `admin_unit` |

<a id="census_2022"></a>

## Fifth Rwanda Population and Housing Census (PHC5), 2022

- Adapter: `pipelines/adapters/census_2022.py` (`Census2022`)
- Publisher: NISR
- Reference year: 2022
- Origin: `official`
- Licence: NISR microdata terms of use: no redistribution
- Where to get it: <https://microdata.statistics.gov.rw>

Expected files (never committed):

- `data/raw/census_2022/*.dta`: Person-level microdata with sector of residence and age
- `data/raw/census_2022/sector_population_age_sex.csv`: Or, without microdata: published sector tables by single year of age and sex

Writes to: `area_indicator`

Indicators: `population_0_2`, `population_3_6`

Checks (loading stops if any fails):

- `sector_match`: Every sector in the file maps to exactly one admin_unit
- `national_total`: National population equals the published PHC5 total
- `district_totals`: District totals equal the published district tables
- `non_negative`: No negative or missing counts

Sector counts are full-count values: write them with low and high left empty. They are the denominators the need model scales to.

<a id="eicv7"></a>

## Integrated Household Living Conditions Survey 7 (EICV7)

- Adapter: `pipelines/adapters/eicv7.py` (`Eicv7`)
- Publisher: NISR
- Reference year: extract date
- Origin: `official`
- Licence: NISR microdata terms of use: no redistribution
- Where to get it: <https://microdata.statistics.gov.rw>

Expected files (never committed):

- `data/raw/eicv7/*household*.dta`: Household file with weight, cluster and stratum
- `data/raw/eicv7/*person*.dta`: Person file with age, sex and activity

Writes to: `area_indicator`

Indicators: `poverty_headcount`

Checks (loading stops if any fails):

- `design_variables`: Weight, cluster and stratum present on every record
- `published_poverty`: District poverty rates reproduce the published report
- `sample_size`: Each district estimate carries its unweighted sample size

EICV is representative at district level. Write district estimates with design-based intervals and sample_size; sector values come from the Phase 2 small-area model, not from this adapter. Set reference_year from the release.

<a id="rdhs_2025"></a>

## Rwanda Demographic and Health Survey 2025

- Adapter: `pipelines/adapters/rdhs_2025.py` (`Rdhs2025`)
- Publisher: NISR, Ministry of Health and The DHS Program
- Reference year: 2025
- Origin: `official`
- Licence: DHS Program dataset terms: registered users, no redistribution
- Where to get it: <https://dhsprogram.com>

Expected files (never committed):

- `data/raw/rdhs_2025/*KR*.DTA`: Children's recode with height-for-age and weights

Writes to: `area_indicator`

Indicators: `stunting_prevalence_u5`

Checks (loading stops if any fails):

- `flagged_measures`: Implausible height-for-age values excluded per DHS rules
- `published_stunting`: District stunting reproduces the published tables (Gicumbi 38.8% is the demo anchor)
- `intervals`: Every district value has a design-based 95% interval

District-level direct estimates only. Sector stunting risk is a Phase 2 model output.

<a id="rdhs_2019_gps"></a>

## Rwanda DHS 2019-20 cluster locations

- Adapter: `pipelines/adapters/rdhs_2019_gps.py` (`Rdhs2019Gps`)
- Publisher: The DHS Program
- Reference year: 2020
- Origin: `official`
- Licence: DHS Program GPS dataset terms: separate request, no redistribution
- Where to get it: <https://dhsprogram.com>

Expected files (never committed):

- `data/raw/rdhs_2019_gps/*GE*/*`: Cluster point file (displaced coordinates)
- `data/raw/rdhs_2019_gps/*KR*.DTA`: Children's recode to join on cluster number

Writes to: `area_indicator`

Indicators: `stunting_prevalence_u5`

Checks (loading stops if any fails):

- `displacement_aware`: Clusters are assigned with their displacement buffer (urban 2 km, rural 5 km); a cluster whose buffer spans sectors is apportioned, never snapped
- `cluster_join`: Every child record joins to one cluster location
- `missing_coordinates`: Clusters at 0,0 are dropped and counted

Feeds the spatial stunting-risk model in Phase 2. Never show cluster points.

<a id="lfs_2025"></a>

## Labour Force Survey 2025

- Adapter: `pipelines/adapters/lfs_2025.py` (`Lfs2025`)
- Publisher: NISR
- Reference year: 2025
- Origin: `official`
- Licence: NISR microdata terms of use: no redistribution
- Where to get it: <https://microdata.statistics.gov.rw>

Expected files (never committed):

- `data/raw/lfs_2025/*.dta`: Person-level file with activity status and reasons

Writes to: `area_indicator`

Indicators: `women_lfp_rate`, `mothers_childcare_barrier_share`

Checks (loading stops if any fails):

- `published_rates`: National and district rates reproduce the LFS report
- `barrier_definition`: Barrier share counts mothers of under-3s outside work who give childcare or family duties as the reason; the variable mapping is recorded in the run
- `sample_size`: Each estimate carries its unweighted sample size

<a id="education_yearbook"></a>

## Education Statistical Yearbook

- Adapter: `pipelines/adapters/education_yearbook.py` (`EducationYearbook`)
- Publisher: MINEDUC
- Reference year: extract date
- Origin: `official`
- Licence: Published statistics; confirm terms for the school list
- Where to get it: <https://www.mineduc.gov.rw>

Expected files (never committed):

- `data/raw/education_yearbook/pre_primary_by_district.csv`: Enrolment and GER
- `data/raw/education_yearbook/schools.csv`: School list with code and location

Writes to: `area_indicator`, `candidate_site`

Indicators: `pre_primary_ger`

Checks (loading stops if any fails):

- `published_ger`: District GER matches the yearbook tables
- `school_codes_unique`: School codes are unique
- `points_in_sector`: Each school point falls in its declared sector

Schools become candidate_site rows of kind 'school' for school-based ECD.

<a id="ncda_mapping"></a>

## NCDA ECD Mapping System and digitised ECD book

- Adapter: `pipelines/adapters/ncda_mapping.py` (`NcdaMapping`)
- Publisher: National Child Development Agency (NCDA)
- Reference year: extract date
- Origin: `partner`
- Licence: Data sharing agreement with NCDA

Expected files (never committed):

- `data/raw/ncda_mapping/centres.csv`: Centre register export with NCDA ids
- `data/raw/ncda_mapping/ecd_book_*.csv`: Digitised weekly ECD book entries

Writes to: `centre`, `weekly_report`

Checks (loading stops if any fails):

- `ncda_ref_unique`: NCDA ids are unique and stored in centre.ncda_ref
- `point_in_sector`: Each centre point falls in its declared sector
- `near_duplicates`: Centres within 50 m with similar names are listed
- `report_rules`: Book entries pass irerero_contract.validation; flagged rows keep their flags
- `no_child_data`: No column holds child names, photos or ids

IrereroAI is a layer on the NCDA system: match on ncda_ref first, then on location and name, and never overwrite a verification done in IrereroAI.

<a id="worldpop"></a>

## WorldPop age and sex structures, constrained, 100 m

- Adapter: `pipelines/adapters/worldpop.py` (`WorldPop`)
- Publisher: WorldPop, University of Southampton
- Reference year: extract date
- Origin: `public`
- Licence: CC BY 4.0
- Where to get it: <https://www.worldpop.org>

Expected files (never committed):

- `data/raw/worldpop/rwa_[fm]_0_*.tif`: Population under 1, by sex
- `data/raw/worldpop/rwa_[fm]_1_*.tif`: Population aged 1 to 4, by sex
- `data/raw/worldpop/rwa_[fm]_5_*.tif`: Population aged 5 to 9, by sex

Writes to: `area_indicator`

Indicators: `population_0_2`, `population_3_6`

Checks (loading stops if any fails):

- `crs`: Rasters are EPSG:4326 with the expected grid
- `census_consistency`: Sector sums are within the agreed tolerance of PHC5
- `nodata`: Nodata cells are excluded, not counted as zero people

Age bands are 0, 1-4 and 5-9: split into 0-2 and 3-6 with census single-year shares. Also used to place village candidate sites at population centres.

<a id="osm"></a>

## OpenStreetMap Rwanda extract

- Adapter: `pipelines/adapters/osm.py` (`Osm`)
- Publisher: OpenStreetMap contributors (via Geofabrik)
- Reference year: extract date
- Origin: `public`
- Licence: ODbL 1.0
- Where to get it: <https://download.geofabrik.de/africa/rwanda.html>

Expected files (never committed):

- `data/raw/osm/rwanda-latest.osm.pbf`: Roads, paths and places

Writes to: `area_indicator`, `candidate_site`

Indicators: `travel_minutes_to_ecd_median`

Checks (loading stops if any fails):

- `network_connected`: The walkable network's main component covers 95% of edges
- `centre_snapping`: Every centre snaps to the network within 500 m
- `extract_date`: The extract date is recorded as the reference date

Replaces the straight-line catchment in CoverageModel with walking time. place=village nodes add village candidate sites.

<a id="boundaries"></a>

## Official administrative boundaries, province to village

- Adapter: `pipelines/adapters/boundaries.py` (`Boundaries`)
- Publisher: NISR
- Reference year: extract date
- Origin: `official`
- Licence: NISR open data terms
- Where to get it: <https://www.statistics.gov.rw>

Expected files (never committed):

- `data/raw/boundaries/*.geojson`: Boundaries per level with official codes

Writes to: `admin_unit`

Checks (loading stops if any fails):

- `unit_counts`: Unit counts per level match NISR's published counts
- `code_crosswalk`: Every existing district and sector code gets a nisr_code; unmatched names go to a manual review list instead of being guessed
- `valid_geometry`: Geometries are valid and nest inside their parent

Phase 1 loads district and sector shapes from geoBoundaries (CC BY 4.0, sourced from NISR open data) in pipelines/demo/geography.py. This adapter adds official codes, cells and villages, and keeps existing codes stable.
