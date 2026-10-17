# Data sources

Generated from the dataset specs in `pipelines/sources/` by `python -m pipelines.sources --write`; do not edit by hand.

Put each file in its folder under `data/raw/` and run the build (`make build`, or `make seed` with Docker). The folder is ignored by git: NISR and DHS licences forbid redistribution, so data never enters the repository.

Every dataset is optional. When a file is missing, the build uses the current demo data in its place, stored with `origin = simulated`, and every screen that shows it carries the SIMULATED DATA badge. When a file is present but does not match its columns, the build stops and says which row and column to fix.

Area files join on the official NISR admin code (`admin_code`) at the level in `admin_level`. Until the official boundaries are loaded, the demo boundaries have no official codes, so give `admin_name` instead; names are matched within their level, ignoring case and accents. Sector names repeat across districts, so add the district in `parent_name` when a name is shared.

Rasters and the OpenStreetMap extract need the geo extras: `uv sync --extra geo`.

```
data/
  raw/                    (gitignored)
    census_2022/            census_2022_areas.csv
    eicv7/                  eicv7_districts.csv
    lfs_2025/               lfs_2025_districts.csv
    rdhs_2025/              rdhs_2025_key_indicators.csv
    education_yearbook/     education_yearbook_2024_25_districts.csv
    worldpop/               rwa_f_0_2020_constrained_UNadj.tif, rwa_f_1_2020_constrained_UNadj.tif, rwa_m_0_2020_constrained_UNadj.tif, rwa_m_1_2020_constrained_UNadj.tif
    boundaries/             provinces.geojson, districts.geojson, sectors.geojson, cells.geojson, villages.geojson
    osm/                    rwanda-latest.osm.pbf
    health_facilities/      health_facilities.csv
    chirps/                 chirps_annual_mm.tif
    srtm/                   srtm_elevation_m.tif
    viirs/                  viirs_radiance.tif
    ecd_centres/            ecd_centres.csv
  contract/               JSON Schemas of the database tables (generated)
```

| # | Dataset | Level | Used by | If missing |
| --- | --- | --- | --- | --- |
| 1 | [Fifth Rwanda Population and Housing Census (PHC5), 2022](#census_2022) | sector | need model: children per sector; need map; optimizer (via need) | Simulated child counts per sector from the demo generator, labelled simulated |
| 2 | [Integrated Household Living Conditions Survey 7 (EICV7), 2023/24](#eicv7) | district | need map: poverty in sector details; national overview | Simulated poverty share per sector; the other values are not shown |
| 3 | [Labour Force Survey 2025](#lfs_2025) | district | need model: mothers' childcare barrier; optimizer: mothers' employment weight | Simulated childcare-barrier share per sector, labelled simulated |
| 4 | [Rwanda Demographic and Health Survey 2025, Key Indicators Report](#rdhs_2025) | district | need model: stunting risk; need map; optimizer: stunting weight | Simulated sector stunting risk around the published Gicumbi value (38.8%), labelled simulated |
| 5 | [Education Statistical Yearbook 2024/25](#education_yearbook) | district | national overview; need map: school readiness context | Not shown until loaded |
| 6 | [WorldPop age and sex structures, constrained, 100 m, 2020 (UN adjusted)](#worldpop) | raster | coverage: where children live inside each sector; catchments and the optimizer | Children spread evenly over each sector's area on the 500 m grid |
| 7 | [Official administrative boundaries, province to village](#boundaries) | village | every map; every area dataset (join key); need model; catchments | geoBoundaries provinces, districts and sectors (public, CC BY 4.0), without official codes; area files then join on admin_name |
| 8 | [OpenStreetMap Rwanda extract](#osm) | road network | catchments: walking time along roads and paths; need map: school, childcare and health facility points | Walking time estimated from straight-line distance x 1.3 at 4 km/h; no facility points |
| 9 | [Health facility locations](#health_facilities) | point | need map: health facility points near planned sites | OpenStreetMap health points when the extract is loaded; otherwise none |
| 10 | [CHIRPS rainfall, annual total](#chirps) | raster | need model (Phase 2): covariate for small-area estimates; need map: sector details | Not used until loaded |
| 11 | [SRTM elevation, 30 m](#srtm) | raster | need model (Phase 2): covariate for small-area estimates; need map: sector details | Not used until loaded |
| 12 | [VIIRS night-time lights, annual composite](#viirs) | raster | need model (Phase 2): covariate for small-area estimates; need map: sector details | Not used until loaded |
| 13 | [NCDA ECD Mapping System: centres, capacity and enrolment](#ecd_centres) | point | catchments and coverage gaps; optimizer: upgrade and support candidates, overcrowding; parent page: nearest centres | Simulated centres for Gicumbi, labelled simulated |

<a id="census_2022"></a>

## 1. Fifth Rwanda Population and Housing Census (PHC5), 2022

- **Folder:** `data/raw/census_2022/`
- **Publisher:** NISR
- **How to get it:** Free registration on the NISR microdata portal; district tables are published — <https://microdata.statistics.gov.rw>
- **Licence:** NISR microdata terms of use: no redistribution
- **Origin label:** `official`
- **Geographic level:** sector
- **Joins on:** admin_code (or admin_name) at sector level; district rows are also accepted
- **Used by:** need model: children per sector; need map; optimizer (via need)
- **Writes:** area_indicator: population_0_2, population_3_6, households_improved_water_share, households_improved_sanitation_share, mothers_secondary_share, mothers_employed_share
- **If missing:** Simulated child counts per sector from the demo generator, labelled simulated

| File | Format | Contents |
| --- | --- | --- |
| `census_2022_areas.csv` | csv | One row per area, aggregated from the microdata or the published tables |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `admin_level` | text | yes | province | district | sector | cell | village of the row |
| `admin_code` | text | no | Official NISR code of the area |
| `admin_name` | text | no | Area name as published; used when admin_code is empty |
| `parent_name` | text | no | Name of the area one level up, when admin_name is shared (sector names repeat across districts) |
| `children_0_2` | whole number ≥ 0 | yes | Children aged 0 to 2, girls and boys |
| `children_3_6` | whole number ≥ 0 | yes | Children aged 3 to 6, girls and boys |
| `households` | whole number ≥ 0 | no | Private households |
| `households_improved_water` | whole number ≥ 0 | no | Households whose main drinking water source is improved |
| `households_improved_sanitation` | whole number ≥ 0 | no | Households with improved sanitation |
| `mothers_u6` | whole number ≥ 0 | no | Mothers of a child under 6 |
| `mothers_u6_secondary` | whole number ≥ 0 | no | Of them, with secondary education or more |
| `mothers_u6_employed` | whole number ≥ 0 | no | Of them, employed |

Sector rows replace the simulated child counts in the pilot district. Girls and boys are summed; the planner does not use the split.

<a id="eicv7"></a>

## 2. Integrated Household Living Conditions Survey 7 (EICV7), 2023/24

- **Folder:** `data/raw/eicv7/`
- **Publisher:** NISR
- **How to get it:** Free registration on the NISR microdata portal — <https://microdata.statistics.gov.rw>
- **Licence:** NISR microdata terms of use: no redistribution
- **Origin label:** `official`
- **Geographic level:** district
- **Joins on:** admin_code (or admin_name) at district level
- **Used by:** need map: poverty in sector details; national overview
- **Writes:** area_indicator: poverty_headcount, pre_primary_attendance_rate, travel_minutes_to_ecd_median
- **If missing:** Simulated poverty share per sector; the other values are not shown

| File | Format | Contents |
| --- | --- | --- |
| `eicv7_districts.csv` | csv | One row per district |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `admin_level` | text | yes | province | district | sector | cell | village of the row |
| `admin_code` | text | no | Official NISR code of the area |
| `admin_name` | text | no | Area name as published; used when admin_code is empty |
| `parent_name` | text | no | Name of the area one level up, when admin_name is shared (sector names repeat across districts) |
| `poverty_headcount` | share, 0 to 1 | yes | Share of people below the poverty line |
| `poverty_headcount_low` | share, 0 to 1 | no | Lower bound of the 95% interval |
| `poverty_headcount_high` | share, 0 to 1 | no | Upper bound of the 95% interval |
| `pre_primary_attendance_rate` | share, 0 to 1 | no | Share of children aged 3 to 6 attending pre-primary |
| `pre_primary_attendance_rate_low` | share, 0 to 1 | no | Lower bound of the 95% interval |
| `pre_primary_attendance_rate_high` | share, 0 to 1 | no | Upper bound of the 95% interval |
| `minutes_to_pre_primary_median` | number | no | Median minutes to the nearest pre-primary school, as reported |
| `sample_size` | whole number ≥ 0 | no | Households interviewed |

Columns ending in _low and _high are the 95% interval. Leave them empty when the source publishes none; the loader then records the value without an interval.

<a id="lfs_2025"></a>

## 3. Labour Force Survey 2025

- **Folder:** `data/raw/lfs_2025/`
- **Publisher:** NISR
- **How to get it:** Free registration on the NISR microdata portal — <https://microdata.statistics.gov.rw>
- **Licence:** NISR microdata terms of use: no redistribution
- **Origin label:** `official`
- **Geographic level:** district
- **Joins on:** admin_code (or admin_name) at district level; province rows are also accepted
- **Used by:** need model: mothers' childcare barrier; optimizer: mothers' employment weight
- **Writes:** area_indicator: women_lfp_rate_mothers_u3, mothers_childcare_barrier_share
- **If missing:** Simulated childcare-barrier share per sector, labelled simulated

| File | Format | Contents |
| --- | --- | --- |
| `lfs_2025_districts.csv` | csv | One row per district |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `admin_level` | text | yes | province | district | sector | cell | village of the row |
| `admin_code` | text | no | Official NISR code of the area |
| `admin_name` | text | no | Area name as published; used when admin_code is empty |
| `parent_name` | text | no | Name of the area one level up, when admin_name is shared (sector names repeat across districts) |
| `women_lfp_rate_mothers_u3` | share, 0 to 1 | yes | Labour force participation of women with a child under 3 |
| `women_lfp_rate_mothers_u3_low` | share, 0 to 1 | no | Lower bound of the 95% interval |
| `women_lfp_rate_mothers_u3_high` | share, 0 to 1 | no | Upper bound of the 95% interval |
| `mothers_childcare_barrier_share` | share, 0 to 1 | no | Mothers of under-3s outside work who give childcare as the reason |
| `mothers_childcare_barrier_share_low` | share, 0 to 1 | no | Lower bound of the 95% interval |
| `mothers_childcare_barrier_share_high` | share, 0 to 1 | no | Upper bound of the 95% interval |
| `sample_size` | whole number ≥ 0 | no | Women in the sample |

Columns ending in _low and _high are the 95% interval. Leave them empty when the source publishes none; the loader then records the value without an interval.

<a id="rdhs_2025"></a>

## 4. Rwanda Demographic and Health Survey 2025, Key Indicators Report

- **Folder:** `data/raw/rdhs_2025/`
- **Publisher:** NISR, Ministry of Health and The DHS Program
- **How to get it:** Public PDF from NISR; copy the district stunting table into the CSV — <https://www.statistics.gov.rw>
- **Licence:** Published report; cite NISR and The DHS Program
- **Origin label:** `official`
- **Geographic level:** district
- **Joins on:** admin_code (or admin_name) at district level
- **Used by:** need model: stunting risk; need map; optimizer: stunting weight
- **Writes:** area_indicator: stunting_prevalence_u5
- **If missing:** Simulated sector stunting risk around the published Gicumbi value (38.8%), labelled simulated

| File | Format | Contents |
| --- | --- | --- |
| `rdhs_2025_key_indicators.csv` | csv | District stunting table typed from the Key Indicators Report |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `admin_level` | text | yes | province | district | sector | cell | village of the row |
| `admin_code` | text | no | Official NISR code of the area |
| `admin_name` | text | no | Area name as published; used when admin_code is empty |
| `parent_name` | text | no | Name of the area one level up, when admin_name is shared (sector names repeat across districts) |
| `stunting_u5` | share, 0 to 1 | yes | Children under 5 below -2 SD height-for-age |
| `stunting_u5_low` | share, 0 to 1 | no | Lower bound of the 95% interval |
| `stunting_u5_high` | share, 0 to 1 | no | Upper bound of the 95% interval |
| `sample_size` | whole number ≥ 0 | no | Children measured |

Columns ending in _low and _high are the 95% interval. Leave them empty when the source publishes none; the loader then records the value without an interval.

Values are shares: write 38.8% as 0.388.

<a id="education_yearbook"></a>

## 5. Education Statistical Yearbook 2024/25

- **Folder:** `data/raw/education_yearbook/`
- **Publisher:** Ministry of Education (MINEDUC)
- **How to get it:** Public PDF; copy the pre-primary district table into the CSV — <https://www.mineduc.gov.rw>
- **Licence:** Published report; cite MINEDUC
- **Origin label:** `official`
- **Geographic level:** district
- **Joins on:** admin_code (or admin_name) at district level
- **Used by:** national overview; need map: school readiness context
- **Writes:** area_indicator: pre_primary_enrolment, pre_primary_ger, ecd_centres
- **If missing:** Not shown until loaded

| File | Format | Contents |
| --- | --- | --- |
| `education_yearbook_2024_25_districts.csv` | csv | Pre-primary enrolment by district typed from the yearbook |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `admin_level` | text | yes | province | district | sector | cell | village of the row |
| `admin_code` | text | no | Official NISR code of the area |
| `admin_name` | text | no | Area name as published; used when admin_code is empty |
| `parent_name` | text | no | Name of the area one level up, when admin_name is shared (sector names repeat across districts) |
| `pre_primary_enrolment` | whole number ≥ 0 | yes | Children enrolled in pre-primary |
| `pre_primary_ger` | number | no | Gross enrolment ratio as a share; it can exceed 1 |
| `pre_primary_schools` | whole number ≥ 0 | no | Schools with pre-primary |

<a id="worldpop"></a>

## 6. WorldPop age and sex structures, constrained, 100 m, 2020 (UN adjusted)

- **Folder:** `data/raw/worldpop/`
- **Publisher:** WorldPop, University of Southampton
- **How to get it:** Open download — <https://hub.worldpop.org/project/categories?id=8>
- **Licence:** CC BY 4.0
- **Origin label:** `public`
- **Geographic level:** raster
- **Joins on:** Pixels summed into 500 m cells inside each pilot sector
- **Used by:** coverage: where children live inside each sector; catchments and the optimizer
- **Writes:** population_cell; area_indicator: population_under5
- **If missing:** Children spread evenly over each sector's area on the 500 m grid

| File | Format | Contents |
| --- | --- | --- |
| `rwa_f_0_2020_constrained_UNadj.tif` | geotiff | Girls under 1 |
| `rwa_f_1_2020_constrained_UNadj.tif` | geotiff | Girls aged 1 to 4 |
| `rwa_m_0_2020_constrained_UNadj.tif` | geotiff | Boys under 1 |
| `rwa_m_1_2020_constrained_UNadj.tif` | geotiff | Boys aged 1 to 4 |

Only where children live is taken from WorldPop; how many comes from the census or the need model. Rename the files to these names if your download differs.

<a id="boundaries"></a>

## 7. Official administrative boundaries, province to village

- **Folder:** `data/raw/boundaries/`
- **Publisher:** NISR, via the Humanitarian Data Exchange (COD-AB)
- **How to get it:** Open download — <https://data.humdata.org/dataset/cod-ab-rwa>
- **Licence:** CC BY 4.0
- **Origin label:** `official`
- **Geographic level:** village
- **Joins on:** admin_code is the key every other dataset joins on
- **Used by:** every map; every area dataset (join key); need model; catchments
- **Writes:** admin_unit (with nisr_code)
- **If missing:** geoBoundaries provinces, districts and sectors (public, CC BY 4.0), without official codes; area files then join on admin_name

| File | Format | Contents |
| --- | --- | --- |
| `provinces.geojson` | geojson | Province polygons |
| `districts.geojson` | geojson | District polygons |
| `sectors.geojson` | geojson | Sector polygons |
| `cells.geojson` | geojson | Cell polygons (optional) |
| `villages.geojson` | geojson | Village polygons (optional) |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `admin_code` | text | yes | Official NISR code |
| `admin_name` | text | yes | Official name |
| `parent_code` | text | no | NISR code of the unit one level up |

Rename the COD-AB columns to admin_code, admin_name and parent_code, and export each level as GeoJSON in EPSG:4326. Cells and villages are optional.

<a id="osm"></a>

## 8. OpenStreetMap Rwanda extract

- **Folder:** `data/raw/osm/`
- **Publisher:** OpenStreetMap contributors, via Geofabrik
- **How to get it:** Open download — <https://download.geofabrik.de/africa/rwanda.html>
- **Licence:** ODbL 1.0
- **Origin label:** `public`
- **Geographic level:** road network
- **Joins on:** Ways and points inside the pilot district, plus a 5 km margin
- **Used by:** catchments: walking time along roads and paths; need map: school, childcare and health facility points
- **Writes:** catchment (walking minutes); facility: school, childcare, health
- **If missing:** Walking time estimated from straight-line distance x 1.3 at 4 km/h; no facility points

| File | Format | Contents |
| --- | --- | --- |
| `rwanda-latest.osm.pbf` | osm.pbf | The whole-country extract from Geofabrik |

Walkable ways: footways, paths, tracks and roads, except private ones. Each place walks in a straight line (x 1.3) to its nearest way.

<a id="health_facilities"></a>

## 9. Health facility locations

- **Folder:** `data/raw/health_facilities/`
- **Publisher:** healthsites.io / Humanitarian Data Exchange
- **How to get it:** Open download — <https://data.humdata.org/dataset/rwanda-healthsites>
- **Licence:** ODbL 1.0
- **Origin label:** `public`
- **Geographic level:** point
- **Joins on:** lon/lat; the sector is the one containing the point
- **Used by:** need map: health facility points near planned sites
- **Writes:** facility: health
- **If missing:** OpenStreetMap health points when the extract is loaded; otherwise none

| File | Format | Contents |
| --- | --- | --- |
| `health_facilities.csv` | csv | One row per facility |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `facility_id` | text | yes | Identifier in the source |
| `name` | text | no | Facility name |
| `facility_type` | text | no | hospital | health_centre | health_post | clinic, as published |
| `lon` | number | yes | Longitude, EPSG:4326 |
| `lat` | number | yes | Latitude, EPSG:4326 |

<a id="chirps"></a>

## 10. CHIRPS rainfall, annual total

- **Folder:** `data/raw/chirps/`
- **Publisher:** Climate Hazards Center, UC Santa Barbara
- **How to get it:** Open download — <https://www.chc.ucsb.edu/data/chirps>
- **Licence:** CC BY 4.0 (public domain dedication for the data)
- **Origin label:** `public`
- **Geographic level:** raster
- **Joins on:** Pixels averaged inside each pilot sector
- **Used by:** need model (Phase 2): covariate for small-area estimates; need map: sector details
- **Writes:** area_indicator: rainfall_mm_annual
- **If missing:** Not used until loaded

| File | Format | Contents |
| --- | --- | --- |
| `chirps_annual_mm.tif` | geotiff | Annual rainfall in mm |

<a id="srtm"></a>

## 11. SRTM elevation, 30 m

- **Folder:** `data/raw/srtm/`
- **Publisher:** NASA / USGS
- **How to get it:** Open download — <https://earthexplorer.usgs.gov>
- **Licence:** Public domain
- **Origin label:** `public`
- **Geographic level:** raster
- **Joins on:** Pixels averaged inside each pilot sector
- **Used by:** need model (Phase 2): covariate for small-area estimates; need map: sector details
- **Writes:** area_indicator: elevation_m_mean, slope_deg_mean
- **If missing:** Not used until loaded

| File | Format | Contents |
| --- | --- | --- |
| `srtm_elevation_m.tif` | geotiff | Elevation in metres |

<a id="viirs"></a>

## 12. VIIRS night-time lights, annual composite

- **Folder:** `data/raw/viirs/`
- **Publisher:** Earth Observation Group, Colorado School of Mines
- **How to get it:** Open download (free registration) — <https://eogdata.mines.edu/products/vnl/>
- **Licence:** CC BY 4.0
- **Origin label:** `public`
- **Geographic level:** raster
- **Joins on:** Pixels averaged inside each pilot sector
- **Used by:** need model (Phase 2): covariate for small-area estimates; need map: sector details
- **Writes:** area_indicator: night_lights_mean
- **If missing:** Not used until loaded

| File | Format | Contents |
| --- | --- | --- |
| `viirs_radiance.tif` | geotiff | Average radiance, nW/cm2/sr |

<a id="ecd_centres"></a>

## 13. NCDA ECD Mapping System: centres, capacity and enrolment

- **Folder:** `data/raw/ecd_centres/`
- **Publisher:** National Child Development Agency (NCDA)
- **How to get it:** Data sharing agreement with NCDA
- **Licence:** NCDA data sharing agreement; not for redistribution
- **Origin label:** `partner`
- **Geographic level:** point
- **Joins on:** lon/lat; the sector is the one containing the point
- **Used by:** catchments and coverage gaps; optimizer: upgrade and support candidates, overcrowding; parent page: nearest centres
- **Writes:** centre; candidate_site: upgrade and support options
- **If missing:** Simulated centres for Gicumbi, labelled simulated

| File | Format | Contents |
| --- | --- | --- |
| `ecd_centres.csv` | csv | Centre register export, one row per centre |

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| `centre_id` | text | yes | NCDA record id |
| `name` | text | yes | Centre name as registered |
| `centre_type` | text | yes | home_based | community_based | school_based | centre_based |
| `lon` | number | yes | Longitude, EPSG:4326 |
| `lat` | number | yes | Latitude, EPSG:4326 |
| `capacity` | whole number ≥ 0 | yes | Children the centre can take |
| `enrolment` | whole number ≥ 0 | yes | Children enrolled in the latest record |
| `enrolment_as_of` | date, YYYY-MM-DD | yes | Date of that record, YYYY-MM-DD |
| `serves_0_2` | yes / no | yes | Takes children aged 0 to 2: yes or no |
| `serves_3_6` | yes / no | yes | Takes children aged 3 to 6: yes or no |
| `offers_meals` | yes / no | yes | Serves at least one meal a day |
| `water_available` | yes / no | yes | Safe drinking water and handwashing on site |
| `verified` | yes / no | no | Verified in the NCDA system |
| `opening_hours` | text | no | e.g. Mo-Fr 07:30-12:00 |
| `fee_band` | text | no | free | under_1000 | from_1000_to_5000 | over_5000 (RWF a month) |
| `offers_growth_monitoring` | yes / no | no | Growth monitoring |
| `disability_inclusive` | yes / no | no | Disability inclusive |

IrereroAI reads the NCDA register and never edits it. A later NCDA API can replace this file without changing anything downstream.
