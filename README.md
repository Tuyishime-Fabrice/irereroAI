<p align="center"><img src="app/assets/logo.png" alt="IrereroAI" width="420"></p>

# IrereroAI

**An AI planning and action platform for early childhood development in Rwanda.**
NISR 2026 Big Data Hackathon, Track 3 (Open Innovation).

> In my district, which sectors need action first, what is holding ECD back there, and are we on
> track for the NST2 target of 65% pre-primary enrolment by 2028/29?

**Live app:** [irereroai.streamlit.app](https://irereroai.streamlit.app/) · **Docs:**
[methodology](docs/methodology.md) · [model card](docs/model_card.md) ·
[limitations](docs/limitations.md) · [data dictionary](docs/data_dictionary.md) ·
[data sources](DATA_SOURCES.md) · [data received](docs/data_inventory.md) ·
[data still needed](docs/data_requests.md)

> **The live app runs on real data.** Census 2022, NISR projections, MINEDUC yearbooks
> 2020/21 to 2024/25, the NISR 2022 boundaries, the MINEDUC school list, OpenStreetMap, EICV7,
> DHS 2025 stunting and the NCDA ECD Mapping extract are all real files. Two parts are not:
> **WorldPop** (incomplete, so a labelled stand-in spreads children evenly inside each sector)
> and the **Muhanga LEARN check-ins and course progress** (simulated by design, labelled
> SIMULATED). The data files stay in a private repository, not here: their licences forbid
> redistribution. Each part of a screen carries its own status.

## Key findings

From the real data (bundle of 30 October 2026), as the app computes them:

- **138,798 more pre-primary places** are needed to reach 65% attendance: 1,055,271 children
  aged 3 to 5 in 2026, 53.5% attending. *Overview, "Places needed" KPI (`irerero/plan/gap.py`).*
- **2 of 30 districts are not on track** for 65% by 2028/29: Kicukiro is off track (projected
  53.2%) and Gasabo at risk (62.7%). This uses MINEDUC's gross rate, already 65.3% nationally
  in 2024/25. *Overview and TRACK, 2028/29 status (`irerero/track/forecast.py`).*
- **In Muhanga, Cyeza, Nyarusange and Nyamabuye** rank first to third with the default "Reach
  most children" weights, and stay in the top three in all 500 weight draws. *District
  priorities (`irerero/plan/priority.py`).*

## Problem and users

NST2 aims to raise pre-primary enrolment to 65% by 2028/29 (54.6% by 2026/27). District
planners must decide where new places go, what is holding attendance back in each sector, and
whether the district is on track, with data spread across the census, MINEDUC yearbooks,
surveys and NCDA's ECD Mapping System.

**Scope: the formal pre-primary gap.** Children aged 3 to 5 attending nursery or pre-primary
school, as counted by the 2022 Census (Table 2.5) and MINEDUC. Census, MINEDUC and NCDA
enrolment figures are never added together. The definition is on every screen.

Four modules form one loop:

| Module | Question | What it gives |
| --- | --- | --- |
| **PLAN** | Where should pre-primary places go? | 2026 estimate of children aged 3 to 5 per sector with a range; places, rooms and caregivers to reach the target; distance to school; priority index with presets and rank stability |
| **DIAGNOSE** | What is holding ECD back? | Five factors, a peer benchmark model (observed vs expected attendance with intervals, top drivers), and a bottleneck with a suggested action |
| **LEARN** | Are caregivers supported? | Monthly centre check-ins (counts only) and four short courses; triggers suggest courses, sector officers confirm (Muhanga pilot, simulated) |
| **TRACK** | Are we on track for 2029? | Trend to 2026/27 and 2028/29 with a range and back-test, status, places a year needed, what-if, and plan decisions with an audit log |

| Role (demo, fictional users) | Sees and does |
| --- | --- |
| District planner | PLAN, DIAGNOSE, TRACK for their district; sets weights and target; approves, edits or rejects; runs what-if; exports the brief |
| National analyst | All districts, read-only on plans; aggregates and the model card |
| Sector officer | LEARN and TRACK for their sector; confirms suggested courses; follows up overdue training |
| Caregiver / teacher | LEARN only: check-ins and their own courses |
| Admin | Users and roles, data files and rebuild; cannot change decisions |

**Screens:** National overview · District priorities · Sector profile · Plan builder and
tracker · Caregiver home · Training (officer) · District brief · Data and methods (plus Admin).

## Quick start

Requires Python 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
make install   # uv sync --extra osm
make data      # build the analysis tables (demo stand-ins for missing files)
make app       # streamlit run app/streamlit_app.py
make test      # 214 tests
```

The app builds the tables itself on first start, so `make app` alone works. Pick a role in the
sidebar.

**Add the real data.** Run `make sources` to create `data/raw/<dataset>/` and list what is
missing. Files received in their own layout (the EICV7 chart, MINEDUC annexes, census sample
records, NISR single-age projections, the NISR 2022 sector boundaries, the NCDA mapping
extract, and the published tables that only verify them) go through
`make intake FILES="<file or folder>"`, which keeps the original read-only, records its
checksum, converts and checks it, and stages it only when complete
([what has been received](docs/data_inventory.md), [what is still needed](docs/data_requests.md)). Put each file where [DATA_SOURCES.md](DATA_SOURCES.md) says, with the columns it
lists, review the spellings in `data/reference/sector_name_crosswalk.csv`, and run `make data`.
Nothing else changes.

**Deploy (Streamlit Community Cloud).** Point the app at `app/streamlit_app.py` and choose
Python 3.11 under Advanced settings; Streamlit Community Cloud installs from `uv.lock` when the repository has one (the main
dependencies only, no extras), so everything the app needs, OSM included, is a main dependency
in `pyproject.toml` (`requirements.txt` mirrors it). It also installs `libgomp1` (needed
by LightGBM) from `packages.txt`. The first start builds the analysis tables (under a minute). Add `DATABASE_URL` (Supabase or Neon Postgres) in
the app's Secrets, so plans, check-ins and the audit log survive restarts. Without it, the app
uses SQLite, which resets when the container restarts.

**Real data on the deployed app, kept private.** The repository never holds received data.
`make bundle` zips the staged tables (never the originals or the census records); the team
keeps the zip in a private repository, and three secrets (`IRERERO_DATA_URL`,
`IRERERO_DATA_TOKEN`, `IRERERO_DATA_SHA256`) let the app fetch it, check its SHA-256 and every
file, and build from it. Without them, or if a check fails, the app stays on the demo data.
Steps: [docs/deploy_private_data.md](docs/deploy_private_data.md).

## Data sources and licences

Twelve datasets. File names, formats, required columns, level, period and licence for each are
in [DATA_SOURCES.md](DATA_SOURCES.md), generated from the loaders' declarations.

| # | Dataset | Publisher | Used by | Licence |
| --- | --- | --- | --- | --- |
| 1 | Census 2022 district profiles (Table 2.5 and household tables) | NISR | PLAN, DIAGNOSE | NISR publication, cited |
| 2 | WorldPop under-5, 100 m, 2020 | WorldPop | PLAN | CC BY 4.0 |
| 3 | Population projections 2023-2032 | NISR | PLAN, TRACK | NISR publication, cited |
| 4 | Administrative boundaries, province to sector | NISR / HDX (fallback geoBoundaries) | maps, joins | CC BY 4.0 |
| 5 | OpenStreetMap Rwanda extract | OSM contributors / Geofabrik | PLAN distance | ODbL 1.0 |
| 6 | MINEDUC statistical yearbooks 2020/21-2024/25 | MINEDUC | DIAGNOSE, TRACK | Government publication, cited |
| 7 | RDHS 2025 stunting by district | NISR, MoH, DHS Program | DIAGNOSE, LEARN trigger | DHS microdata terms; district rates only |
| 8 | EICV7 poverty | NISR | PLAN, DIAGNOSE | NISR publication, cited |
| 9 | National ECD Standards (2024), as parameters | NCDA | PLAN, LEARN | Government publication, cited |
| 10 | Course source materials | NCDA, UNICEF, WHO | LEARN | Adapted and cited |
| 11 | NCDA ECD Mapping extract (`supply_extract`) | NCDA | LEARN, connector | NCDA data sharing agreement; shown only when `IRERERO_NCDA_DISPLAY` is on |
| 12 | Check-ins and course progress, Muhanga | IrereroAI generator | LEARN | Simulated |

## Status legend

Every number carries its source, reference period and status on hover and in exports.

| Status | Meaning |
| --- | --- |
| observed | Counted in a census, yearbook or administrative record |
| published estimate | Estimate published by its producer (projections, survey rates) |
| model estimate | Computed by IrereroAI from observed and published inputs |
| user input | Entered in the app (targets, weights, decisions, check-ins) |
| **simulated** | Stand-in while the real file is missing. Red badge; excluded from exports by default |

## Methods

Summary below; formulas and code references are in [docs/methodology.md](docs/methodology.md).

- **2026 children aged 3 to 5:** NISR district projection × census 3-5 share, split across
  sectors by WorldPop under-5 (× census age ratio) or by census shares, with a range.
- **Places** = max(0, ⌈t·P⌉ − A); **rooms** = ⌈places/30⌉; **caregivers** between places/30 and
  places/15 (National ECD Standards 2024).
- **Distance:** share of children more than 1 km from a school (OSM schools and the MINEDUC
  list, a shared site counted once), along OSM roads where they reach most children, otherwise
  straight-line and labelled *indicative*; provisional while the school lists are partial.
- **Priority:** weighted percentile ranks of volume, equity, peer gap and poverty, with three
  presets or custom weights. Rank stability is the share of 500 Dirichlet weight draws in
  which a sector stays in the top 3.
- **Peer model:** province and district means, weighted linear regression and LightGBM,
  compared by leave-one-district-out CV; the simplest within 1 point of the best is kept;
  80% split-conformal intervals; top 3 drivers (associations).
- **Bottlenecks:** SUPPLY, DEMAND, CAPACITY, WELLBEING or NONE, by explicit rules, each with an
  action.
- **TRACK:** linear trend of MINEDUC gross enrolment with an 80% prediction interval;
  back-test on 2024/25; on track / at risk / off track.

## Results

Measured on the real data with `make data`; details in [docs/model_card.md](docs/model_card.md).

| Peer model (leave-one-district-out) | MAE (points) | Weighted MAE | R² |
| --- | --- | --- | --- |
| Province mean | 13.05 | 12.09 | -0.13 |
| **District mean (kept)** | **9.21** | **8.61** | **0.40** |
| Weighted linear regression | 12.79 | 11.97 | -0.04 |
| LightGBM | 11.57 | 11.16 | 0.07 |

- Neither model beats the district mean, so the district mean is kept: each sector is compared
  with the other sectors of its district.
- 80% conformal intervals: ±14.9 points; coverage 80.3% (rural 81.2%, urban 75.0%).
- Residual Moran's I: 0.142 (p = 0.001).
- 2029 trend back-test (fit 2020/21 to 2023/24, predict 2024/25): MAE 5.10 points; 100% of
  districts inside the 80% range.

The 214 tests check data integrity (sums, joins, duplicates, sources and statuses), the formulas
(hand-checked), the model and rules, the audit entries for each decision and confirmation,
simulated-value labelling and exclusion from exports, the training triggers on the planted
problems, that every screen renders for every role, and the assistant end to end (figures,
roles, follow-ups, errors) against a local stand-in for the Messages API.

## Privacy and ethics

- **Law No. 058/2021 on the protection of personal data and privacy.** IrereroAI works with
  aggregates only. It holds no child records, names, photos or IDs, and the check-in collects
  counts only. Demo users are fictional.
- **People decide.** The system suggests; planners approve, edit or reject, with a reason
  required for edits and rejections. Sector officers confirm courses. Nothing becomes required
  or funded automatically.
- **Append-only audit log.** Every decision, status change, course confirmation and check-in
  records who, when, before, after and why. Entries cannot be edited or deleted.
- **No causal claims.** Drivers are labelled "associated with, not caused by".
- **No ranking of caregivers.** Quiz scores are private to the caregiver; officers see averages
  over at least three caregivers. The quiz measures course knowledge, not teaching quality.
- **Small numbers.** Counts of children under 10 are exported as "fewer than 10".
- **Raw data never enters git.** A pre-commit hook and CI block data formats and the raw
  folders.
- **The assistant explains, people decide.** It reads aggregates only, cannot change
  anything, and its answers are marked as written by an AI model.

## Relationship to NCDA

IrereroAI **complements** NCDA's ECD Mapping System; it does not replace it. NCDA maps centres.
IrereroAI adds the planning layer: where the gap is, why, and whether the district is on
track. It is built to read an NCDA extract in the `supply_extract` schema:

| Column | Meaning |
| --- | --- |
| `centre_id` | NCDA centre identifier (unique) |
| `name` | Centre name |
| `centre_type` | school_based, community_based, home_based, centre_based, other, not_stated |
| `district_name`, `sector_name` | Joined to geo_id through the reviewed crosswalk |
| `lon`, `lat` | WGS84 location |
| `capacity`, `enrolled_3_5`, `enrolled_3_6`, `caregivers` | Places, children aged 3 to 5 enrolled, children aged 3 to 6 enrolled (the NCDA extract's band), caregivers; empty where the source has no such field |
| `as_of` | Extract date (YYYY-MM-DD) |

`make intake` converts NCDA's own export (`ncda_ecd_mapping_extract.csv`) to this schema:
active services only, no value derived (the extract has no capacity and counts ages 3 to 6). The
Data and methods screen shows mapped services by sector, real ones only when
`IRERERO_NCDA_DISPLAY` is on. Mapped services do not join the distance layer, which measures
distance to formal pre-primary schools. The LEARN demo keeps its 36 simulated Muhanga centres
(seed 2026), labelled SIMULATED, in demo mode only. NCDA enrolment is never added to census or
MINEDUC counts.

## Limitations

See [docs/limitations.md](docs/limitations.md). In short:

- WorldPop is incomplete: children are spread evenly inside each sector.
- LEARN check-ins and course progress are simulated.
- Census attendance may miss home-based ECD.
- One projection variant only.
- OSM does not mark pre-primary.
- Five yearbook points make a short trend.
- District context is applied to every sector.
- LEARN content and Kinyarwanda labels are drafts awaiting review.

**Cut from scope, by design:** weekly centre reporting, child records, child tests or games,
SMS/USSD, and any cost optimiser in RWF.

## IrereroAI assistant

Planners can ask questions about the dashboard in plain language ("Why is this district
behind the target?", "How many places are needed?", "What does the scope warning mean?").
On each role's home screen (the Overview, Caregiver learning for sector officers and
caregivers, Admin) the question box sits at the top of the page; every other screen has an
**Ask IrereroAI** button that opens the same conversation in a dialog.

- **Answers come from the dashboard's own figures.** The assistant (Claude, through the
  official Anthropic SDK, server side) gets a snapshot of the screen the person is on (page,
  filters, target, the figures shown) and five read-only tools that call the same functions
  the screens use (`irerero/assistant/facts.py`): overview, district comparison, a district's
  needs, trend and sector ranking, a sector's diagnosis, and which data are real. It computes
  no figure of its own, labels every figure with its status (simulated values say so), and is
  told to say when the data needed are missing instead of guessing.
- **Roles hold.** Tools refuse what a role cannot open in the app (a sector officer sees their
  own sector; a planner sees sector detail for their own district only).
- **Conversations** keep their history for follow-up questions, are append-only (earlier turns
  go back unchanged), and reset when the user or demo role changes. Errors (no network, rate
  limits, service errors, a wrong key) show a plain message and, where it helps, Try again.
- **Setup.** Add `ANTHROPIC_API_KEY` to the app's Secrets (Streamlit Cloud) or environment.
  Optional: `IRERERO_ASSISTANT_MODEL` (default `claude-haiku-5-5`),
  `IRERERO_ASSISTANT_EFFORT` (default `medium`), `IRERERO_ASSISTANT_FALLBACKS=on` to use the
  server-side refusal fallback with a model that has one (off by default: Claude Haiku 5.5
  has none). Without a key the question box is
  disabled and says the assistant is not set up; it never pretends to answer.
- **Privacy.** Only aggregate dashboard figures and the person's question are sent to
  Anthropic's API. The question box asks people not to type personal information.
- **Tests** run without a key against `tests/fake_anthropic.py`, a local stand-in that speaks
  the streaming wire format and checks the conversation stays append-only.

## AI-use disclosure

The code, tests and documentation were written with the help of AI coding tools, directed
and reviewed by the team. The app's planning layer is
the statistical and machine-learning work described above: calibrated estimates, the peer
benchmark model with conformal intervals, rank stability and rule-based diagnosis. Every model
output carries its status and uncertainty, and people make the decisions. The optional
IrereroAI assistant uses generative AI (Claude, by Anthropic) to explain those figures; its
answers are labelled as AI-written and it cannot change plans, weights or data.

## Team

| Name | Role |
| --- | --- |
| Mutimutuje Daniella Dewelly | Team leader and project manager |
| Tuyishime Fabrice | Data scientist and developer |

Contact: fabricetuyishime2050@gmail.com

## Repository layout

```
app/                 Streamlit entry point, screens (views/) and brand assets
irerero/             Python package
  data/              dataset declarations, loaders, validation, crosswalk, demo generator
  pipeline/          make data: observations, estimates, model, forecast, content
  plan/ diagnose/ track/ learn/   the four modules
  db/                SQLAlchemy models (SQLite or Postgres)
  assistant/         IrereroAI assistant: dashboard facts, AI conversation loop
  ui/                design system, charts, maps, the assistant's screens
content/courses/     LEARN lessons (Markdown) and quizzes (JSON)
data/demo/           committed stand-ins (simulated tables, simplified boundaries)
data/reference/      crosswalks to review
docs/                methodology, model card, limitations, data dictionary
tests/               pytest suite
```
