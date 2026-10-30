# Methodology

IrereroAI answers one question for a district: which sectors need action first, what is holding
early childhood development back there, and are we on track for the NST2 target of 65%
pre-primary enrolment by 2028/29? Four modules form a loop: **PLAN → DIAGNOSE → LEARN → TRACK**.

**Scope: the formal pre-primary gap.** Children aged 3 to 5 attending nursery or pre-primary
school, as counted by the 2022 Census (Table 2.5) and MINEDUC. Home-based ECD may not be
included. Census, MINEDUC and NCDA enrolment figures are never added together. Where two
sources meet, one only *moves* the other (a trend or a share), and the screen says which.

Parameters live in `irerero/config.py`, each with its citation. Code references are given so
every step can be checked.

## Data layer

- One loader per dataset (`irerero/data/sources/`) with a declared schema
  ([DATA_SOURCES.md](../DATA_SOURCES.md)). Errors name the file, column and line.
- A missing file falls back to the committed demo bundle (`data/demo/`), in the same format.
  Every value read from it has the status **simulated**.
- Names join to `geo_id` only through the reviewed crosswalks in `data/reference/`. Matching
  ignores case and spacing only; any unmatched name stops the build with the list.
- `make data` writes every input value to `observation` (geo_id, indicator, value, period,
  source, page, status) and rebuilds the analysis tables. App tables (plans, check-ins, course
  progress, audit log) keep their rows.

Checks run on every build and in CI: sector rows add up to district totals; attending plus
never attended equals the total; all 416 sectors join to the boundaries; no duplicate
(geo_id, indicator, period); every observation has a source and a status.

## PLAN: where to put pre-primary places

### 2026 estimate of children aged 3 to 5 (`irerero/plan/estimate.py`)

1. **District total.** NISR projected population for 2026 × the district's census 2022 share of
   children aged 3 to 5.
2. **Sector split.** WorldPop 2020 under-5 counts summed per sector (100 m grids, zonal sum) ×
   the district's census ratio of 3-5 to 0-4 children, normalised within the district. While
   WorldPop is missing, the census 2022 sector shares are used.
3. **Range.** Relative half-width √(p² + d²): *p* is half the NISR projection range (or 3% when
   the projection gives no range) and *d* is the gap between the WorldPop and census sector
   shares (or 5% for drift since 2022 when only the census is available).
4. **Attending.** The sector's census 2022 attendance rate × the district's change in MINEDUC
   pupils per child from 2021/22 (the census school year) to 2024/25, capped at 98%.

### Places, rooms and caregivers (`irerero/plan/gap.py`)

For a planner-set target *t* (default 65%), *P* children and *A* attending:

- places = max(0, ⌈t·P⌉ − A)
- rooms = ⌈places / 30⌉
- caregivers between ⌈places / 30⌉ and ⌈places / 15⌉

These are the National ECD Standards (2024) norms. Products are rounded to 6 decimals before
the ceiling, so 0.65 × 100 gives 65 places, not 66.

### Distance (`irerero/plan/distance.py`)

The share of children aged 3 to 5 who live more than 1 km from a school with pre-primary.

- **Children** are the WorldPop pixels inside the sector. While WorldPop is missing, points on
  an even 250 m grid stand in.
- **Schools** are OSM `amenity=school` and `amenity=kindergarten` or, while OSM is missing, the
  MINEDUC school list (provisional). NCDA-mapped services are not added (`NCDA_IN_DISTANCE` in
  `irerero/config.py` is off): most are home-based ECD, not formal pre-primary schools, and the
  simulated demo centres must never shorten a real distance.
- **Distance** is the walk along OSM walkable roads, using Dijkstra from a virtual source that
  joins each school to its nearest road node, with a 1 km cutoff. A point counts as on the
  network if it lies within 500 m of a road. A sector uses road distance only when at least
  half its children are on the network. Otherwise it uses straight-line distance, labelled
  **indicative**.

### Priority index (`irerero/plan/priority.py`)

Four components, each converted to a percentile rank among the sectors of the district:

| Component | Measure |
| --- | --- |
| Volume | places needed at the target |
| Equity | share of children aged 3 to 5 not attending |
| Peer gap | expected minus observed attendance from DIAGNOSE, floored at 0 |
| Poverty | EICV7 poverty rate (sector, else district) |

The score is the weighted sum of the percentile ranks. Presets: Reach most children
0.50/0.20/0.15/0.15, Equity first 0.15/0.40/0.15/0.30, Balanced 0.30/0.30/0.20/0.20, or custom
weights. A component without data drops out and its weight is shared in proportion.

**Rank stability.** We draw 500 weight vectors from a Dirichlet distribution centred on the
chosen weights (concentration 40) and record the share of draws in which each sector stays in
the top 3: *stable* (≥ 80%), *depends on weights* (40-80%), *rarely top 3* (< 40%).

## DIAGNOSE: what is holding ECD back

### Five factors (`irerero/diagnose/rules.py`)

Each factor is a national percentile, where 1 means worst.

| Factor | Level | Parts |
| --- | --- | --- |
| Access | sector | non-attendance, share beyond 1 km |
| Capacity | district context | pupils per teacher, pupils per classroom, unqualified teachers, plus 1 − LEARN required-training completion |
| Wellbeing | district context | stunting, RDHS 2025 |
| Home environment | sector | no improved water, no improved sanitation, women without secondary education |
| Poverty | sector, else district | EICV7 poverty rate |

District factors rank the 30 districts and are shown as *district context*, never as sector
values.

### Peer benchmark model (`irerero/diagnose/peer.py`)

The model estimates the census 2022 attendance rate we would expect for a sector, given six
features: urban share, women with secondary education, improved water, electricity, poverty,
and log children per km².

| Candidate | Prediction for a sector |
| --- | --- |
| Province mean | Weighted mean of the other districts' sectors in the same province |
| District mean | Weighted mean of the other sectors in the same district (leave one sector out). It uses the district's own information, so it is a strong bar. |
| Linear regression | Weighted (by children aged 3 to 5) linear regression on standardised features |
| LightGBM | 300 trees, 7 leaves, learning rate 0.03, at least 12 samples per leaf, with subsampling |

- **Validation:** leave-one-district-out cross-validation, reporting MAE in percentage points
  and R². The simplest candidate within 1 point of the best MAE is kept.
- **Expected values** are out-of-fold. A sector's expectation never uses its own district's
  data (models) or its own value (district mean).
- **Intervals:** 80% split-conformal. The half-width is the k-th smallest absolute
  out-of-fold residual, with k = ⌈(n+1)·0.8⌉.
- **Drivers:** for the linear model, coefficient × standardised value; for LightGBM, SHAP
  values. The top 3 per sector are shown as *associated with, not caused by*.
- **Diagnostics:** Moran's I on residuals (queen contiguity, 999 permutations), error by
  urban/rural and by province, and interval coverage by area.
- **Fallback:** if a baseline is kept, no model beats the district average. The peer gap then
  leaves the priority index, and each sector is compared with the average of the other
  sectors in its district.

### Bottleneck rules

The first rule that applies is the main bottleneck. Others are listed as "also flagged".

| Condition | Bottleneck | Action |
| --- | --- | --- |
| Estimated attendance ≥ target | NONE | Monitor |
| Non-attendance in the national top half and ≥ 30% of children beyond 1 km | SUPPLY | Build or expand rooms (number given) |
| Fewer than 30% beyond 1 km and observed attendance below the peer interval | DEMAND | Parent outreach; check fees and awareness |
| District capacity score ≥ 0.75 | CAPACITY | Recruit and train caregivers (number given); assign LEARN *ECD Standards essentials* |
| Stunting, water or sanitation score ≥ 0.75 | WELLBEING | Link with nutrition and WASH programmes; assign LEARN courses |
| Below target, none of the above | SUPPLY | Expand places at nearby schools |

The rules run live at the planner's target and with the latest LEARN completion.

## LEARN: caregivers (pilot district Muhanga, simulated)

- **Check-in** (`irerero/learn/checkins.py`): monthly, counts only. It records enrolled
  children, average attendance, caregivers present, meal days (0-6 a week), water and
  handwashing (yes/no) and the main challenge. Labels are in English and Kinyarwanda.
- **Courses** (`content/courses/`): two are required on joining (ECD Standards essentials, Child
  safeguarding basics). Two are triggered: Hygiene and WASH, and Nutrition and growth
  monitoring. Each has 3-5 lessons and a 5-question quiz; 4 of 5 completes the course.
- **Triggers** (`irerero/learn/triggers.py`):
  - A check-in with no water flags WASH.
  - Fewer than 3 meal days flags nutrition.
  - A sector with water or sanitation in the worst national quarter flags WASH for its
    caregivers.
  - A district with stunting in the worst quarter flags nutrition.
  - Flags stay *recommended* until the sector officer confirms them with a due date, which is
    audited, or sets them aside with a reason. Nothing becomes required automatically.
- **Aggregates only:** officers see completion by centre and sector, overdue courses, and an
  average quiz score only over at least three caregivers. Scores are private to the caregiver.
  Caregivers are never ranked. The quiz measures course knowledge, not teaching quality.
- **Capacity feedback:** the share of caregivers per district who completed their required
  courses enters the DIAGNOSE capacity factor.

## TRACK: are we on track for 2029?

- **Rate** (`irerero/track/forecast.py`): MINEDUC pre-primary pupils / children aged 3 to 5
  (NISR projection × census 3-5 share), by district and nationally, 2020/21 to 2024/25. Pupils
  include over-age children, so this is a gross rate.
- **Trend:** ordinary least squares on the five points, projected to 2026/27 (NST2 milestone
  54.6%) and 2028/29 (65%), with an 80% prediction interval.
- **Status:**
  - *On track:* the projection is at or above the target.
  - *At risk:* the projection is below, but the interval reaches the target.
  - *Off track:* even the top of the interval is below the target.
- **Back-test:** fit 2020/21 to 2023/24, predict 2024/25; we report the error and whether the
  observed value fell inside the interval.
- **Places per year needed:** (t × children in 2028/29 − pupils in 2024/25) / 4.
- **What-if:** N rooms a year from 2026/27, each place filled, added to the trend. Places
  beyond what the chosen sectors (or the whole district) need to reach the target stay empty
  and add nothing; a warning shows when that happens.
- **Plans** (`irerero/track/plans.py`): recommendations become plan items. The district
  planner approves, edits or rejects each one; edits and rejections need a reason. Items move
  through planned → funded → done.
- **Audit log** (`irerero/audit.py`): every change writes one append-only row recording who,
  when, before, after and why.

## Exports (`irerero/brief.py`)

The district brief cites every number. The CSV is long: one row per value with its source,
period and status. Simulated values are excluded unless the user includes them, in which case
they are labelled. Counts of children under 10 are written as "fewer than 10".
