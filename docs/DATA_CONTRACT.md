# Data contract

This is the shape every dataset takes inside IrereroAI. Phase 1 fills it with simulated data
for Gicumbi; Phase 2 loads real sources into exactly the same tables, so the API and the web
app do not change.

The tables are defined once, in `packages/contract/src/irerero_contract/tables/`. Column
comments are the field documentation: they are written to Postgres, exported to the JSON
Schemas in [`data/contract/`](../data/contract/) and rendered into the field reference at the
end of this page. Run `uv run python -m irerero_contract.export` after changing a table; CI
fails when the schemas or this page are out of date.

## Rules that hold for every record

**Provenance on everything.** Every statistical or reported record carries:

| Field | Meaning |
| --- | --- |
| `source` | Named source, e.g. "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | Year the values describe |
| `origin` | `official`, `public`, `partner` or `simulated` |
| `pipeline_run_id` | The run that loaded the row; null for records entered through the app |

The web app reads `origin` to show source badges and the SIMULATED DATA label. Records derived
from other records (scenarios, recommendations, alerts) take the weakest origin of their inputs:
if any input is simulated, the output is simulated.

**Counts and areas only.** No table holds a child's name, photo, identifier or exact home
location. Weekly reports are counts per centre. Parent locations are snapped to a 500 m grid
cell before they are stored (see demand signals below).

**Geometry.** Stored in EPSG:4326. Areas and distances are computed in EPSG:32735 (UTM zone 35S).
Boundaries are stored at three levels of detail (`geom`, `geom_medium`, `geom_coarse`) so maps
load fast at every zoom.

**Estimates come with ranges.** Need estimates store `_estimate`, `_low` and `_high` for every
value, with a CHECK constraint that `low <= estimate <= high`. Area indicators store `low` and
`high` when the source gives an interval, and `sample_size` when it is survey-based.

**Code lists, not free text.** Every categorical field is a code from
`irerero_contract.enums`, enforced by a CHECK constraint. Codes are stored as text so a Phase 2
migration can extend a list.

## Administrative codes

`admin_unit.code` is a stable IrereroAI code built from names, for example `D-GICUMBI` for the
district and `S-GICUMBI-BYUMBA` for a sector. Every table joins on it.

`admin_unit.nisr_code` holds the official NISR code. The boundary files used in Phase 1
(geoBoundaries, CC BY 4.0, sourced from NISR open data) do not carry official codes, so the
column is empty today. The Phase 2 `boundaries` adapter fills it through a crosswalk and sends
any name it cannot match to a manual review list. Real data sources then align on `nisr_code`.

## Weekly report validation

Implemented once in `irerero_contract.validation` and used by the web form, the SMS parser, the
API and the NCDA adapter.

| Outcome | Rule | Effect |
| --- | --- | --- |
| Error | Negative counts; days above 6; average attendance above enrolment; meal days above open days; children with disability above enrolment; attendance on a week with no open days | Report refused with a plain-language message |
| Needs confirmation | Enrolment above 1.5 times capacity; no caregiver on an open week; more than 25 children per caregiver; waiting list above 3 times capacity | Reporter must confirm; the report is stored with `out_of_range_confirmed` |
| Quality flag | Enrolment or attendance moves by more than 30% and more than 10 children against the median of the centre's last 4 reports | Stored with `enrolment_jump` or `attendance_jump`, shown to the sector officer |

Nothing is silently accepted or silently dropped.

## Suppression of small counts

Public pages and CSV exports replace any count below 5 with "fewer than 5" (`null` plus a
`suppressed: true` marker in the API). The rule lives in one function in the API and applies to
every public and export endpoint.

## Demand signals

A parent search with no result, or a "request a centre here" tap, writes one `demand_signal`.
The API converts the location to EPSG:32735, snaps it to the 500 m grid cell that contains it,
and stores only the cell id (`E{easting}N{northing}` of the cell's south-west corner) and the
cell centre. The raw coordinates never reach the database or the logs.

## Rejection reasons become constraints

When a planner rejects a recommendation, the reason code changes the next optimizer run:

| Code | Effect on the next run |
| --- | --- |
| `no_land` | The site is excluded |
| `already_funded` | The site is excluded |
| `community_objection` | The site is excluded |
| `access_problem` | The site's catchment is halved |
| `other` | No automatic effect; the free text is shown to the next planner |

## Audit log

`audit_log` is append-only: a database trigger rejects UPDATE, DELETE and TRUNCATE. Every
approve, edit, reject, centre verification, alert status change and role change writes one row
with the values before and after.

## Files Phase 2 loads

Each loadable table has a JSON Schema in `data/contract/<table>.schema.json`. Adapters may read
any source format, but what they hand to `load` must validate against these schemas:

- tabular data as CSV or JSON Lines with the schema's field names;
- geometry as GeoJSON in EPSG:4326 (the schemas reject coordinates outside Rwanda's bounding box,
  which catches swapped axes and projected coordinates);
- every row with the provenance fields above.

The adapter for each source, its expected input files and its checks are listed in
[PHASE2_HANDOFF.md](PHASE2_HANDOFF.md).

## Field reference

<!-- BEGIN GENERATED FIELD REFERENCE -->

### Indicator codes

| Code | Unit | Meaning |
| --- | --- | --- |
| `population_0_2` | count | Children aged 0 to 2 |
| `population_3_6` | count | Children aged 3 to 6 |
| `stunting_prevalence_u5` | share | Children under 5 below -2 SD height-for-age |
| `poverty_headcount` | share | Share of people below the national poverty line |
| `pre_primary_ger` | share | Pre-primary gross enrolment ratio |
| `women_lfp_rate` | share | Labour force participation rate, women 16+ |
| `mothers_childcare_barrier_share` | share | Mothers of under-3s outside work who give childcare as the reason |
| `ecd_centres` | count | ECD centres registered in the area |
| `travel_minutes_to_ecd_median` | minutes | Median walking time from a home to the nearest ECD centre |

### `admin_unit`

Administrative areas from country down to village, with geometry simplified per zoom.

JSON Schema: [`data/contract/admin_unit.schema.json`](../data/contract/admin_unit.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `code` | string | key | Stable IrereroAI code, e.g. D-GICUMBI or S-GICUMBI-BYUMBA. All tables join on it |
| `name` | string | yes | Official name as published |
| `level` | code | yes | country \| province \| district \| sector \| cell \| village |
| `parent_code` | string |  | Code of the enclosing unit |
| `nisr_code` | string |  | Official NISR administrative code. Filled by the Phase 2 boundaries adapter |
| `source_ref` | string |  | Identifier in the boundary source, e.g. the geoBoundaries shapeID |
| `geom` | multipolygon 4326 | yes | Boundary, EPSG:4326, full detail |
| `geom_medium` | multipolygon 4326 | yes | Boundary simplified for district zoom (about 50 m tolerance) |
| `geom_coarse` | multipolygon 4326 | yes | Boundary simplified for national zoom (about 500 m tolerance) |
| `centroid` | point 4326 | yes | Point on surface, EPSG:4326 |
| `area_km2` | float | yes | Area computed in EPSG:32735 (UTM 35S) |
| `source` | string | yes | Named source, for example "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | smallinteger | yes | Year the values describe, not the year they were loaded |
| `origin` | code | yes | official \| public \| partner \| simulated. Drives UI badges |
| `pipeline_run_id` | uuid |  | Pipeline run that loaded the row. Null for records entered through the app |

### `alert`

An early-warning signal for one centre and week, with its reason in plain words.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Id |
| `centre_code` | string | yes | Centre concerned |
| `week_start` | date | yes | Week the signal fired |
| `kind` | code | yes | attendance_drop \| missing_report \| overcrowding \| wash \| closure_risk |
| `severity` | code | yes | info \| warning \| critical |
| `reason_en` | text | yes | Reason in English |
| `reason_rw` | text | yes | Reason in Kinyarwanda |
| `evidence` | json | yes | Numbers the rule used, e.g. {attendance, baseline_mean, z_score} |
| `rule` | string | yes | Rule id inside the early-warning model |
| `model_version_id` | string | yes | Early-warning version |
| `origin` | code | yes | Origin of the reports the alert was computed from |
| `status` | code | yes | open \| acknowledged \| resolved |
| `assigned_to` | uuid |  | Officer following up |
| `resolution_note` | text |  | What was done |
| `created_at` | datetime | yes | When the row was written |
| `updated_at` | datetime | yes | Last status change |

### `area_indicator`

Source indicators aligned to an area. Phase 2 adapters write here; models read here.

JSON Schema: [`data/contract/area_indicator.schema.json`](../data/contract/area_indicator.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Row id |
| `area_code` | string | yes | Area the value describes |
| `indicator` | string | yes | Indicator code from docs/DATA_CONTRACT.md#indicators |
| `value` | float | yes | Value in the indicator's unit |
| `low` | float |  | Lower bound when the source gives one |
| `high` | float |  | Upper bound when the source gives one |
| `unit` | string | yes | count \| share \| minutes \| rwf |
| `sample_size` | integer |  | Survey respondents behind the value, when survey-based |
| `reference_date` | date |  | Exact date when finer than reference_year |
| `source` | string | yes | Named source, for example "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | smallinteger | yes | Year the values describe, not the year they were loaded |
| `origin` | code | yes | official \| public \| partner \| simulated. Drives UI badges |
| `pipeline_run_id` | uuid |  | Pipeline run that loaded the row. Null for records entered through the app |

### `audit_log`

Append-only record of every human decision. A trigger rejects UPDATE and DELETE.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | biginteger | key | Id |
| `actor_id` | uuid |  | Account that acted |
| `actor_role` | code | yes | Role at the time |
| `action` | string | yes | e.g. recommendation.reject, centre.verify, alert.resolve |
| `entity_type` | string | yes | Table of the changed row |
| `entity_id` | string | yes | Key of the changed row |
| `before` | json |  | Values before |
| `after` | json |  | Values after |
| `reason` | text |  | Reason given by the person |
| `created_at` | datetime | yes | When the row was written |

### `candidate_site`

A place where an action could happen: a village or school to build at, or a centre.

JSON Schema: [`data/contract/candidate_site.schema.json`](../data/contract/candidate_site.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | key | Site code |
| `kind` | code | yes | village \| school \| centre_upgrade \| centre_support |
| `name` | string | yes | Village, school or centre name |
| `sector_code` | string | yes | Sector of the site |
| `centre_code` | string |  | Existing centre for upgrade and support sites |
| `location` | point 4326 | yes | Site location, EPSG:4326 |
| `unit_cost_band` | code | yes | Cost band looked up in unit_cost |
| `source` | string | yes | Named source, for example "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | smallinteger | yes | Year the values describe, not the year they were loaded |
| `origin` | code | yes | official \| public \| partner \| simulated. Drives UI badges |
| `pipeline_run_id` | uuid |  | Pipeline run that loaded the row. Null for records entered through the app |

### `centre`

An ECD centre. Mirrors the NCDA ECD Mapping System record so a connector can sync it.

JSON Schema: [`data/contract/centre.schema.json`](../data/contract/centre.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `code` | string | key | IrereroAI centre code |
| `name` | string | yes | Centre name as registered |
| `type` | code | yes | home_based \| community_based \| school_based \| centre_based |
| `status` | code | yes | active \| closed |
| `sector_code` | string | yes | Sector the centre is in |
| `location` | point 4326 | yes | Centre location, EPSG:4326 |
| `capacity` | integer | yes | Number of children the centre can take |
| `serves_0_2` | boolean | yes | Takes children aged 0 to 2 |
| `serves_3_6` | boolean | yes | Takes children aged 3 to 6 |
| `opening_hours` | string | yes | OpenStreetMap opening_hours syntax, e.g. "Mo-Fr 07:30-12:00" |
| `fee_band` | code | yes | Monthly fee per child in RWF: free \| under_1000 \| from_1000_to_5000 \| over_5000 |
| `offers_meals` | boolean | yes | Serves at least one meal a day |
| `offers_growth_monitoring` | boolean | yes | Hosts growth monitoring or refers to it |
| `disability_inclusive` | boolean | yes | Has adapted space and trained caregivers for children with disabilities |
| `verified` | boolean | yes | A sector officer has checked the centre in person |
| `verified_at` | datetime |  | When the last verification happened |
| `verified_by` | uuid |  | Officer who verified the centre |
| `reliability_score` | float | yes | 0 to 1. Share of the last 12 weeks reported on time without quality flags |
| `ncda_ref` | string |  | Record identifier in the NCDA ECD Mapping System |
| `source` | string | yes | Named source, for example "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | smallinteger | yes | Year the values describe, not the year they were loaded |
| `origin` | code | yes | official \| public \| partner \| simulated. Drives UI badges |
| `pipeline_run_id` | uuid |  | Pipeline run that loaded the row. Null for records entered through the app |

### `coverage_snapshot`

Weekly coverage per sector. Produced by CoverageModel from centres and need.

JSON Schema: [`data/contract/coverage_snapshot.schema.json`](../data/contract/coverage_snapshot.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Row id |
| `area_code` | string | yes | Sector |
| `week_start` | date | yes | Monday of the week |
| `model_version_id` | string | yes | Coverage model that produced the row |
| `children_covered` | integer | yes | Children 0 to 6 with a place within the catchment |
| `children_uncovered` | integer | yes | Children 0 to 6 without a reachable place |
| `overcrowded_centres` | integer | yes | Centres with attendance above capacity |
| `catchment_minutes` | smallinteger | yes | Walking time used for the catchment |
| `source` | string | yes | Named source, for example "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | smallinteger | yes | Year the values describe, not the year they were loaded |
| `origin` | code | yes | official \| public \| partner \| simulated. Drives UI badges |
| `pipeline_run_id` | uuid |  | Pipeline run that loaded the row. Null for records entered through the app |

### `data_source`

Catalogue of every source the platform uses or will use, and its status today.

JSON Schema: [`data/contract/data_source.schema.json`](../data/contract/data_source.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | key | Adapter name, e.g. census_2022 |
| `name` | string | yes | Human-readable source name |
| `publisher` | string | yes | Publishing institution |
| `reference_year` | smallinteger |  | Year described |
| `origin` | code | yes | Origin once loaded |
| `status` | code | yes | loaded \| simulated_stand_in \| planned |
| `licence` | string | yes | Licence or access terms |
| `url` | string |  | Where the source is published |
| `feeds` | json | yes | Tables or indicators this source feeds |

### `decision`

A person's verdict on a recommendation. Rejection reasons feed the next run.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Id |
| `recommendation_id` | uuid | yes | Recommendation |
| `user_id` | uuid | yes | Person who decided |
| `verdict` | code | yes | approve \| edit \| reject |
| `reason_code` | code |  | no_land \| already_funded \| access_problem \| community_objection \| other |
| `reason_text` | text |  | Free-text explanation |
| `edits` | json |  | Changed fields for an edit: {field: {from, to}} |
| `created_at` | datetime | yes | When the row was written |

### `demand_signal`

A parent search with no result, or a request for a centre. The raw parent location is never stored: the API snaps it to a 500 m grid cell in EPSG:32735 before anything is written.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Id |
| `kind` | code | yes | empty_search \| centre_request |
| `grid_cell` | string | yes | 500 m cell id in EPSG:32735: 'E{easting}N{northing}' |
| `cell_centre` | point 4326 | yes | Centre of the cell, EPSG:4326 |
| `sector_code` | string | yes | Sector containing the cell centre |
| `age_band` | string |  | Age band searched for: 0_2 \| 3_6 |
| `origin` | code | yes | Origin of the signal |
| `created_at` | datetime | yes | When the row was written |

### `model_version`

A versioned engine component. Phase 1 baselines and Phase 2 trained models live here.

JSON Schema: [`data/contract/model_version.schema.json`](../data/contract/model_version.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | key | Version id, e.g. need-baseline-1 |
| `component` | code | yes | need \| coverage \| optimizer \| early_warning \| explainer |
| `description` | text | yes | What the model does, in plain words |
| `params` | json | yes | Parameters and thresholds |
| `metrics` | json | yes | Evaluation metrics. Empty for rule-based baselines |
| `trained_on_run_id` | uuid |  | Pipeline run that produced the training data |
| `created_at` | datetime | yes | When the row was written |

### `need_estimate`

Estimated need per area with an interval for every value. Produced by NeedEstimator.

JSON Schema: [`data/contract/need_estimate.schema.json`](../data/contract/need_estimate.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Row id |
| `area_code` | string | yes | Sector for district deep dives, district for the national map |
| `model_version_id` | string | yes | Model that produced the estimate |
| `children_0_2_estimate` | integer | yes | Children aged 0 to 2, point estimate |
| `children_0_2_low` | integer | yes | Children aged 0 to 2, lower bound |
| `children_0_2_high` | integer | yes | Children aged 0 to 2, upper bound |
| `children_3_6_estimate` | integer | yes | Children aged 3 to 6, point estimate |
| `children_3_6_low` | integer | yes | Children aged 3 to 6, lower bound |
| `children_3_6_high` | integer | yes | Children aged 3 to 6, upper bound |
| `stunting_risk_estimate` | float | yes | Share of under-5s at risk of stunting |
| `stunting_risk_low` | float | yes | Stunting risk, lower bound |
| `stunting_risk_high` | float | yes | Stunting risk, upper bound |
| `mothers_barrier_share_estimate` | float | yes | Share of mothers of under-3s who report childcare as a barrier to work |
| `mothers_barrier_share_low` | float | yes | Mothers' childcare barrier, lower bound |
| `mothers_barrier_share_high` | float | yes | Mothers' childcare barrier, upper bound |
| `top_drivers` | json | yes | Up to five drivers: [{feature, label_en, label_rw, contribution}] |
| `source` | string | yes | Named source, for example "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | smallinteger | yes | Year the values describe, not the year they were loaded |
| `origin` | code | yes | official \| public \| partner \| simulated. Drives UI badges |
| `pipeline_run_id` | uuid |  | Pipeline run that loaded the row. Null for records entered through the app |

### `otp_challenge`

One-time sign-in code for parents. Only the hash of the code is stored.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Id |
| `phone` | string | yes | E.164 phone |
| `code_hash` | string | yes | Argon2id hash of the code |
| `attempts` | smallinteger | yes | Failed attempts |
| `expires_at` | datetime | yes | Expiry |
| `consumed_at` | datetime |  | Used |
| `created_at` | datetime | yes | When the row was written |

### `pipeline_run`

One execution of an adapter or the demo generator, with its checks.

JSON Schema: [`data/contract/pipeline_run.schema.json`](../data/contract/pipeline_run.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Run id |
| `pipeline` | string | yes | Adapter or generator name, e.g. demo_generator |
| `origin` | code | yes | Origin of the rows loaded |
| `status` | code | yes | running \| succeeded \| failed |
| `started_at` | datetime | yes | Start time |
| `finished_at` | datetime |  | End time |
| `code_version` | string | yes | Git commit or package version |
| `inputs` | json | yes | Input files with sha256 and size: [{path, sha256, bytes}] |
| `row_counts` | json | yes | Rows written per table |
| `checks` | json | yes | Checks run: [{name, passed, detail}] |

### `planning_default`

Default budget and policy weights for an area, set by national analysts.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `area_code` | string | key | District, or RW for national |
| `budget_rwf` | biginteger | yes | Default budget in RWF |
| `weight_stunting` | float | yes | Default stunting weight |
| `weight_readiness` | float | yes | Default readiness weight |
| `weight_jobs` | float | yes | Default jobs weight |
| `updated_by` | uuid |  | Analyst who last changed it |
| `updated_at` | datetime | yes | When the row was written |

### `recommendation`

One ranked suggestion in a scenario. Never acted on until a person approves it.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Id |
| `scenario_id` | uuid | yes | Scenario |
| `rank` | integer | yes | 1 is the strongest suggestion |
| `action` | code | yes | build \| upgrade \| support |
| `site_id` | string | yes | Target site or centre |
| `children_reached` | integer | yes | Uncovered children 0 to 6 who gain a reachable place |
| `reached_low` | integer | yes | Children reached, lower bound |
| `reached_high` | integer | yes | Children reached, upper bound |
| `high_risk_children_reached` | integer | yes | Children reached in high stunting-risk areas |
| `mothers_under3_reached` | integer | yes | Mothers of under-3s in the catchment who report childcare as a barrier |
| `cost_rwf` | biginteger | yes | Expected cost in RWF |
| `score` | float | yes | Weighted benefit per RWF used to rank |
| `drivers` | json | yes | Top reasons: [{feature, label_en, label_rw, contribution}] |
| `sources` | json | yes | Inputs used: [{table, source, reference_year, origin}] |
| `status` | code | yes | proposed \| approved \| edited \| rejected |

### `refresh_token`

Issued refresh tokens, so they can be rotated and revoked.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Token id |
| `user_id` | uuid | yes | Owner |
| `expires_at` | datetime | yes | Expiry |
| `revoked_at` | datetime |  | Set on rotation or sign-out |
| `created_at` | datetime | yes | When the row was written |

### `saved_search`

A parent's saved search. Location is snapped to the 500 m grid, like demand signals.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Id |
| `user_id` | uuid | yes | Parent |
| `label` | string | yes | Name the parent gave it |
| `grid_cell` | string | yes | 500 m cell id |
| `cell_centre` | point 4326 | yes | Centre of the cell, EPSG:4326 |
| `filters` | json | yes | {age_band, meals, max_fee_band, max_km} |
| `created_at` | datetime | yes | When the row was written |

### `scenario`

A planning run: budget, policy weights and constraints chosen by a person.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Id |
| `district_code` | string | yes | District being planned |
| `name` | string | yes | Label shown in comparisons |
| `budget_rwf` | biginteger | yes | Budget in RWF |
| `weight_stunting` | float | yes | Policy weight on high stunting risk |
| `weight_readiness` | float | yes | Policy weight on uncovered 3 to 6 year olds |
| `weight_jobs` | float | yes | Policy weight on mothers' childcare barrier |
| `constraints` | json | yes | Extra constraints: {excluded_site_ids, max_actions_per_sector} |
| `is_baseline` | boolean | yes | True for the largest-population-first comparison run |
| `model_version_id` | string | yes | Optimizer version |
| `origin` | code | yes | simulated when any input record is simulated |
| `created_by` | uuid | yes | Planner who ran it |
| `created_at` | datetime | yes | When the row was written |

### `unit_cost`

Cost of one action by cost band, used by the optimizer and the what-if simulator.

JSON Schema: [`data/contract/unit_cost.schema.json`](../data/contract/unit_cost.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `action` | code | key | build \| upgrade \| support |
| `band` | code | key | low \| medium \| high |
| `cost_rwf` | biginteger | yes | Expected cost in RWF |
| `cost_low_rwf` | biginteger | yes | Lower bound in RWF |
| `cost_high_rwf` | biginteger | yes | Upper bound in RWF |
| `places_added` | integer | yes | New places the action creates |
| `source` | string | yes | Named source, for example "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | smallinteger | yes | Year the values describe, not the year they were loaded |
| `origin` | code | yes | official \| public \| partner \| simulated. Drives UI badges |
| `pipeline_run_id` | uuid |  | Pipeline run that loaded the row. Null for records entered through the app |

### `user_account`

Staff, caregivers and parents. Role and scope are copied into every access token.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Id |
| `role` | code | yes | Role |
| `scope_level` | code | yes | none \| centre \| sector \| district \| national |
| `scope_code` | string |  | Centre code or admin unit code the account may see |
| `display_name` | string | yes | Name shown in the app |
| `email` | string |  | Staff login |
| `phone` | string |  | E.164 phone, parent and caregiver login |
| `password_hash` | string |  | Argon2id hash |
| `totp_secret` | string |  | TOTP secret. Required for admins |
| `is_active` | boolean | yes | Can sign in |
| `created_at` | datetime | yes | When the row was written |

### `weekly_report`

The weekly centre report: about ten counts, no child-level data.

JSON Schema: [`data/contract/weekly_report.schema.json`](../data/contract/weekly_report.schema.json)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | uuid | key | Report id |
| `centre_code` | string | yes | Reporting centre |
| `week_start` | date | yes | Monday of the reported week |
| `enrolled_0_2_female` | integer | yes | Girls aged 0 to 2 enrolled |
| `enrolled_0_2_male` | integer | yes | Boys aged 0 to 2 enrolled |
| `enrolled_3_6_female` | integer | yes | Girls aged 3 to 6 enrolled |
| `enrolled_3_6_male` | integer | yes | Boys aged 3 to 6 enrolled |
| `avg_daily_attendance` | integer | yes | Average number of children present per open day |
| `waiting_list` | integer | yes | Children waiting for a place |
| `caregivers_present` | integer | yes | Caregivers present on a typical day |
| `days_open` | smallinteger | yes | Days the centre opened this week, 0 to 6 |
| `days_meal_served` | smallinteger | yes | Days a meal was served, 0 to 6 |
| `wash_available` | boolean | yes | Water and handwashing were available all week |
| `referrals_growth_monitoring` | integer | yes | Children referred to growth monitoring this week |
| `children_with_disability` | integer | yes | Enrolled children with a known disability |
| `main_problem` | code | yes | none \| no_food \| no_water \| caregiver_absent \| building_damage \| weather \| other |
| `channel` | code | yes | web \| offline \| sms \| assisted |
| `quality_flags` | list | yes | Validation flags. Flagged reports are kept and shown, never silently accepted |
| `submitted_by` | uuid |  | Account that submitted or entered the report |
| `submitted_at` | datetime | yes | When the server received it |
| `source` | string | yes | Named source, for example "NISR Census 2022" or "IrereroAI demo generator" |
| `reference_year` | smallinteger | yes | Year the values describe, not the year they were loaded |
| `origin` | code | yes | official \| public \| partner \| simulated. Drives UI badges |
| `pipeline_run_id` | uuid |  | Pipeline run that loaded the row. Null for records entered through the app |

<!-- END GENERATED FIELD REFERENCE -->
