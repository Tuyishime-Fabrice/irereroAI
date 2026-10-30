<p align="center"><img src="app/assets/logo.png" alt="IrereroAI" width="420"></p>

# IrereroAI

IrereroAI helps district planners in Rwanda decide where to expand pre-primary education, understand what is holding enrolment back in each sector, and check whether the district is on track for the NST2 target.

NISR 2026 Big Data Hackathon, Track 3: Open Innovation

**Live app:** [irereroai.streamlit.app](https://irereroai.streamlit.app/)
**Documentation:** [methodology](docs/methodology.md) · [model card](docs/model_card.md) · [limitations](docs/limitations.md) · [data dictionary](docs/data_dictionary.md) · [data sources](DATA_SOURCES.md)

## The problem

NST2 sets a target of 65% pre-primary enrolment by 2028/29, with 54.6% as the 2026/27 milestone. To reach it, every district has to answer three questions: which sectors need new places first, why attendance is low where it is low, and whether progress is fast enough.

The data to answer these questions exists, but it is spread across the census, MINEDUC yearbooks, household surveys and NCDA's ECD Mapping System, and it rarely reaches planners at sector level in a usable form. IrereroAI brings these sources together in one place.

We focus on formal pre-primary: children aged 3 to 5 attending nursery or pre-primary school, as counted by the 2022 Census and MINEDUC. Census, MINEDUC and NCDA figures are never added together, and this definition is shown on every screen.

## What the app does

The app has four modules that work as a cycle.

| Module | Question | What the user gets |
|---|---|---|
| PLAN | Where should new places go? | Children aged 3 to 5 per sector in 2026, the places, classrooms and caregivers needed to reach the target, distance to the nearest school, and a priority ranking of sectors |
| DIAGNOSE | What is holding enrolment back? | Each sector's attendance compared with similar sectors, the factors most associated with the gap, and the main bottleneck with a suggested action |
| LEARN | Are caregivers supported? | Monthly centre check-ins and four short courses for caregivers, suggested by the system and confirmed by sector officers |
| TRACK | Are we on track for 2029? | The enrolment trend to 2026/27 and 2028/29, an on track, at risk or off track status, places needed per year, what-if scenarios and a record of plan decisions |

Each user sees what their role needs. District planners use PLAN, DIAGNOSE and TRACK for their district and approve or reject proposals. National analysts see all districts in read-only mode. Sector officers use LEARN and TRACK and confirm courses. Caregivers see only their own check-ins and courses. An admin manages users and data files but cannot change decisions. All users in the demo are fictional.

## Data

| Dataset | Publisher | Used for |
|---|---|---|
| [Fifth Population and Housing Census (PHC5), 2022](https://www.statistics.gov.rw/data-sources/censuses/Population-and-Housing-Census/fifth-population-and-housing-census-2022/main-indicators-5th-rwanda-population-and-housing-census-phc) | NISR | Children aged 3 to 5, pre-primary attendance and household context (PLAN, DIAGNOSE) |
| Subnational Population Projections 2023-2032 for [provinces](https://gis.statistics.gov.rw/data-sources/censuses/Population-and-Housing-Census/fifth-population-and-housing-census-2022/rwanda-subnational-population-projections-provinces-2023-2032) and [districts](https://gis.statistics.gov.rw/data-sources/censuses/Population-and-Housing-Census/fifth-population-and-housing-census-2022/rwanda-subnational-population-projections-districts-2023-2032) | NISR | Population in 2026 and future need (PLAN, TRACK) |
| [Integrated Household Living Conditions Survey (EICV7), 2023/24](https://microdata.statistics.gov.rw/index.php/catalog/119/get_microdata) | NISR | Poverty indicators (PLAN, DIAGNOSE) |
| [Rwanda Demographic and Health Survey (DHS), 2025](https://microdata.worldbank.org/catalog/8555/get-microdata) | NISR, Ministry of Health, The DHS Program | Stunting and child wellbeing by district (DIAGNOSE) |
| [Sector boundaries, 2022](https://services5.arcgis.com/deNm5epdmeZgcm16/ArcGIS/rest/services/Sector_Boundary_2022/FeatureServer/1) | NISR | Maps and joining data across sources |
| Education Statistical Yearbooks 2020/21 to 2024/25 and pre-primary school locations | MINEDUC | Enrolment trend, school locations and capacity (DIAGNOSE, TRACK) |
| WorldPop Rwanda population, [2020](https://hub.worldpop.org/geodata/summary?id=49708) and [2015-2030](https://hub.worldpop.org/geodata/summary?id=50514) | WorldPop, University of Southampton | Where young children live within each district (PLAN) |
| [OpenStreetMap Rwanda extract](https://download.geofabrik.de/africa/rwanda.html) | OpenStreetMap contributors, Geofabrik | Roads and distance to school (PLAN) |
| National ECD Standards, 2024 | NCDA | Class size and caregiver ratios (PLAN, LEARN) |
| ECD course materials | NCDA, UNICEF, WHO | Course content (LEARN) |
| ECD Mapping System extract | NCDA | Centres, capacity and caregivers. Simulated for Muhanga until a data-sharing approval is in place (PLAN) |
| Caregiver check-ins and course progress | IrereroAI data generator | Simulated, because the platform has not yet been used by caregivers (LEARN) |

Where an official file was not available in a usable format in time, we compiled the figures from published reports and marked them as provisional.

**Data storage.** Raw data files are not in this repository. Redistribution rights are not confirmed for every dataset and some have sharing conditions, so we keep them in a private repository limited to the team. Licences, file formats and required columns for each dataset are listed in [DATA_SOURCES.md](DATA_SOURCES.md).

**Every number shows where it comes from.** On hover and in exports, each figure carries its source, reference period and status: observed, published estimate, model estimate, user input or simulated. Simulated values have a red badge and are left out of exports by default.

## How it works

- **Children aged 3 to 5 in 2026.** NISR district projections, split across sectors using WorldPop under-5 population (or census shares), with a low and high range.
- **Places needed.** The extra children who must attend to reach the target. Classrooms assume 30 children each, and caregiver needs range from one per 30 to one per 15 children, following the National ECD Standards (2024).
- **Distance to school.** The share of children living more than 1 km from a school, measured along OSM roads where possible. Where roads do not reach, we use straight-line distance and label it indicative.
- **Priority ranking.** Sectors are ranked on four factors: number of children without a place, equity, gap compared with similar sectors, and poverty. Planners choose one of three presets or set their own weights. We also show how stable each ranking is: the share of 500 random weightings in which a sector stays in the top 3.
- **Peer comparison.** We compared province and district averages, a weighted linear regression and LightGBM using leave-one-district-out cross-validation, and kept the simplest model within 1 point of the best. Each estimate has an 80% interval. The factors shown are associations, not causes.
- **Bottlenecks.** Clear rules classify each sector as supply, demand, capacity, wellbeing or no major bottleneck, and each type is linked to a suggested action.
- **Tracking.** A linear trend of MINEDUC gross enrolment with an 80% prediction interval, back-tested on 2024/25.

Full formulas and code references are in [docs/methodology.md](docs/methodology.md).

## Results

Peer model, leave-one-district-out cross-validation:

| Model | MAE (points) | R² |
|---|---|---|
| Province mean | 8.41 | 0.40 |
| District mean | 8.52 | 0.35 |
| **Weighted linear regression (chosen)** | **3.85** | **0.88** |
| LightGBM | 4.11 | 0.87 |

- The 80% intervals covered 80.3% of cases (85% rural, 61% urban).
- Some spatial pattern remains in the errors (Moran's I 0.30, p = 0.001), which we report as a limitation.
- The enrolment trend back-test had a mean error of 0.95 points, with 93% of districts inside the 80% range.

These figures were measured on the demo build and show that the pipeline works as intended. They are not a measure of real-world accuracy. Details are in the [model card](docs/model_card.md).

The project has 99 automated tests covering data integrity, the formulas (checked by hand), the model and rules, the audit log, the labelling of simulated values, and that every screen loads for every role.

## Privacy and responsible use

- **Aggregates only.** In line with Law No. 058/2021 on the protection of personal data and privacy, IrereroAI holds no child records, names, photos or IDs. Check-ins collect counts only.
- **People make the decisions.** The system suggests; planners approve, edit or reject, and must give a reason for edits and rejections. Sector officers confirm courses. Nothing is funded or made mandatory automatically.
- **Audit log.** Every decision, confirmation and check-in records who, when, what changed and why. Entries cannot be edited or deleted.
- **No ranking of caregivers.** Quiz scores are private. Officers see only averages across at least three caregivers.
- **Small numbers.** Counts under 10 are exported as "fewer than 10".
- **No raw data in git.** A pre-commit hook and CI checks block data files.

## Working with NCDA

IrereroAI complements NCDA's ECD Mapping System; it does not replace it. NCDA maps the centres, and IrereroAI adds the planning layer on top: where the gap is, why, and whether the district is on track. It can read an NCDA extract with these columns:

`centre_id, name, centre_type, district_name, sector_name, lon, lat, capacity, enrolled_3_5, caregivers, as_of`

The demo uses a simulated extract for Muhanga District.

## Limitations

- Census attendance may miss home-based ECD.
- The share of children aged 3 to 5 is held at its 2022 level.
- OpenStreetMap does not tag pre-primary schools specifically.
- Five yearbook data points make a short trend.
- District-level indicators such as stunting and poverty are applied to every sector in that district.
- LEARN content and Kinyarwanda labels are drafts awaiting expert review.

We deliberately left out child-level records, weekly centre reporting, SMS/USSD, a chatbot and cost optimisation. More detail is in [docs/limitations.md](docs/limitations.md).

## Running it locally

Requires Python 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
make install   # install dependencies
make data      # build the analysis tables
make app       # start the app
make test      # run the tests
```

`make app` builds the tables on first run if they are missing. To load the real data, run `make sources` to see which files are expected, place them as described in [DATA_SOURCES.md](DATA_SOURCES.md), check the spellings in `data/reference/sector_name_crosswalk.csv`, then run `make data`.

The live app runs on Streamlit Community Cloud. Set `DATABASE_URL` (Postgres) in the app secrets so that plans and check-ins survive restarts; without it, the app uses SQLite, which resets when the server restarts.

## Repository layout

```
app/              Streamlit app, screens and assets
irerero/          Python package: data loading, pipeline and the four modules
content/courses/  LEARN lessons and quizzes
data/demo/        simulated stand-ins and simplified boundaries
data/reference/   name crosswalks
docs/             methodology, model card, limitations, data dictionary
tests/            test suite
```

## AI-use disclosure

We used Claude Code, an AI coding assistant by Anthropic, to help write the code, tests and documentation. The team directed the work, reviewed and tested all of it, and takes full responsibility for the result. The app itself does not use generative AI. Its analysis is the statistical and machine learning layer described above, and every model output shows its uncertainty so that people make the final decisions.

## Team

| Name | Role |
|---|---|
| Mutimutuje Daniella Dewelly | Team leader and project manager |
| Tuyishime Fabrice | Data scientist and developer |

Contact: fabricetuyishime2050@gmail.com
