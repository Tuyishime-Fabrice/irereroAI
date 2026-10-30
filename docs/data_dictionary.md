# Data dictionary

Generated from `irerero/db/models.py` by `python -m irerero.docs --write`; do not edit by hand. Analysis tables are rebuilt by `make data`; app tables keep their rows.

## `geo_unit` (analysis)

Country, provinces, districts and sectors. geo_id: RW, P-<NAME>, D-<NAME>, S-<DISTRICT>-<SECTOR>; nisr_code once the crosswalk is reviewed.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `geo_id` | VARCHAR(64) | no | primary |
| `level` | VARCHAR(16) | no |  |
| `name` | VARCHAR(120) | no |  |
| `parent_id` | VARCHAR(64) | yes |  |
| `nisr_code` | VARCHAR(16) | yes |  |
| `province` | VARCHAR(64) | yes |  |
| `district` | VARCHAR(64) | yes |  |
| `area_km2` | FLOAT | yes |  |

## `source` (analysis)

Every dataset, whether its real file was loaded, and its licence.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `source_id` | VARCHAR(64) | no | primary |
| `title` | VARCHAR(200) | no |  |
| `publisher` | VARCHAR(160) | no |  |
| `reference_period` | VARCHAR(32) | no |  |
| `url` | VARCHAR(300) | yes |  |
| `licence` | VARCHAR(160) | no |  |
| `loaded` | BOOLEAN | no |  |
| `notes` | TEXT | yes |  |

## `observation` (analysis)

Every input value: where, what, when, from which source and page, with its status. One row per geo_id, indicator and period.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `id` | INTEGER | no | primary |
| `geo_id` | VARCHAR(64) | no | → geo_unit.geo_id |
| `indicator_id` | VARCHAR(64) | no |  |
| `value` | FLOAT | no |  |
| `reference_period` | VARCHAR(16) | no |  |
| `source_id` | VARCHAR(64) | no | → source.source_id |
| `source_page` | VARCHAR(32) | yes |  |
| `status` | VARCHAR(24) | no |  |
| `qa_flag` | VARCHAR(120) | yes |  |

## `estimate_2026` (analysis)

PLAN: children aged 3 to 5 in 2026 with a range, attendance, and the share more than 1 km from a school.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `geo_id` | VARCHAR(64) | no | primary |
| `children_3_5` | FLOAT | no |  |
| `low` | FLOAT | no |  |
| `high` | FLOAT | no |  |
| `attendance_rate_2022` | FLOAT | no |  |
| `attendance_rate` | FLOAT | no |  |
| `attending` | FLOAT | no |  |
| `far_share` | FLOAT | yes |  |
| `distance_method` | VARCHAR(64) | yes |  |
| `children_spread` | VARCHAR(24) | yes |  |
| `status` | VARCHAR(24) | no |  |
| `method` | TEXT | no |  |

## `model_run` (analysis)

DIAGNOSE: each peer-model candidate with its cross-validation metrics; the chosen one also holds the diagnostics (coverage, Moran's I, error breakdowns).

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `model_id` | VARCHAR(48) | no | primary |
| `chosen` | BOOLEAN | no |  |
| `metrics` | JSON | no |  |

## `model_output` (analysis)

DIAGNOSE: observed and expected attendance per sector with the 80% interval and top drivers (associations).

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `geo_id` | VARCHAR(64) | no | primary |
| `model_id` | VARCHAR(48) | no |  |
| `observed` | FLOAT | no |  |
| `expected` | FLOAT | no |  |
| `low` | FLOAT | no |  |
| `high` | FLOAT | no |  |
| `drivers` | JSON | no |  |
| `status` | VARCHAR(24) | no |  |

## `diagnosis` (analysis)

DIAGNOSE: five factor scores, the main bottleneck, the action and the reasons, at the default target.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `geo_id` | VARCHAR(64) | no | primary |
| `access` | FLOAT | yes |  |
| `capacity` | FLOAT | yes |  |
| `wellbeing` | FLOAT | yes |  |
| `home` | FLOAT | yes |  |
| `poverty` | FLOAT | yes |  |
| `bottleneck` | VARCHAR(16) | no |  |
| `intervention` | TEXT | no |  |
| `reasons` | JSON | no |  |
| `details` | JSON | no |  |
| `status` | VARCHAR(24) | no |  |

## `forecast` (analysis)

TRACK: enrolment rate per district and nationally: observed years, projected years with a range, and the back-test.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `geo_id` | VARCHAR(64) | no | primary |
| `year` | VARCHAR(8) | no | primary |
| `kind` | VARCHAR(16) | no | primary |
| `value` | FLOAT | no |  |
| `children` | FLOAT | yes |  |
| `pupils` | FLOAT | yes |  |
| `low` | FLOAT | yes |  |
| `high` | FLOAT | yes |  |
| `status` | VARCHAR(24) | no |  |

## `supply_extract` (analysis)

NCDA ECD Mapping extract in the connector schema (simulated for Muhanga in the demo).

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `centre_id` | VARCHAR(32) | no | primary |
| `name` | VARCHAR(160) | no |  |
| `centre_type` | VARCHAR(24) | no |  |
| `geo_id` | VARCHAR(64) | no | → geo_unit.geo_id |
| `lon` | FLOAT | no |  |
| `lat` | FLOAT | no |  |
| `capacity` | INTEGER | yes |  |
| `enrolled_3_5` | INTEGER | yes |  |
| `enrolled_3_6` | INTEGER | yes |  |
| `caregivers` | INTEGER | yes |  |
| `as_of` | DATE | no |  |
| `status` | VARCHAR(24) | no |  |

## `course` (analysis)

LEARN: the four courses, English and Kinyarwanda titles, trigger and source.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `course_id` | VARCHAR(48) | no | primary |
| `position` | INTEGER | no |  |
| `title_en` | VARCHAR(160) | no |  |
| `title_rw` | VARCHAR(160) | no |  |
| `required_on_joining` | BOOLEAN | no |  |
| `trigger` | VARCHAR(48) | yes |  |
| `source` | TEXT | no |  |

## `lesson` (analysis)

LEARN: lesson text (Markdown) per course.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `id` | VARCHAR(64) | no | primary |
| `course_id` | VARCHAR(48) | no | → course.course_id |
| `position` | INTEGER | no |  |
| `title` | VARCHAR(160) | no |  |
| `body_md` | TEXT | no |  |

## `quiz_item` (analysis)

LEARN: five quiz questions per course.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `id` | VARCHAR(64) | no | primary |
| `course_id` | VARCHAR(48) | no | → course.course_id |
| `position` | INTEGER | no |  |
| `question` | TEXT | no |  |
| `options` | JSON | no |  |
| `answer` | INTEGER | no |  |

## `app_user` (app)

Users and roles (demo users are fictional).

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `user_id` | VARCHAR(48) | no | primary |
| `role` | VARCHAR(24) | no |  |
| `name` | VARCHAR(120) | no |  |
| `district_id` | VARCHAR(64) | yes |  |
| `sector_id` | VARCHAR(64) | yes |  |
| `centre_id` | VARCHAR(32) | yes |  |

## `plan` (app)

TRACK: a district plan with its target and priority weights.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `plan_id` | INTEGER | no | primary |
| `district_id` | VARCHAR(64) | no |  |
| `name` | VARCHAR(120) | no |  |
| `target` | FLOAT | no |  |
| `preset` | VARCHAR(48) | no |  |
| `weights` | JSON | no |  |
| `created_by` | VARCHAR(48) | no |  |
| `created_at` | DATETIME | no |  |

## `plan_item` (app)

TRACK: one recommendation in a plan, its decision, reason and status.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `id` | INTEGER | no | primary |
| `plan_id` | INTEGER | no | → plan.plan_id |
| `geo_id` | VARCHAR(64) | no |  |
| `rank` | INTEGER | no |  |
| `places` | INTEGER | no |  |
| `rooms` | INTEGER | no |  |
| `caregivers_low` | INTEGER | no |  |
| `caregivers_high` | INTEGER | no |  |
| `bottleneck` | VARCHAR(16) | no |  |
| `intervention` | TEXT | no |  |
| `decision` | VARCHAR(16) | no |  |
| `reason` | TEXT | yes |  |
| `status` | VARCHAR(16) | no |  |
| `decided_by` | VARCHAR(48) | yes |  |
| `decided_at` | DATETIME | yes |  |

## `centre_checkin` (app)

LEARN: monthly centre check-in, counts only.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `id` | INTEGER | no | primary |
| `centre_id` | VARCHAR(32) | no |  |
| `month` | VARCHAR(7) | no |  |
| `enrolled` | INTEGER | no |  |
| `attendance_avg` | FLOAT | no |  |
| `caregivers_present` | INTEGER | no |  |
| `meal_days_avg` | FLOAT | no |  |
| `water_available` | BOOLEAN | no |  |
| `main_challenge` | VARCHAR(24) | no |  |
| `submitted_by` | VARCHAR(48) | no |  |
| `submitted_at` | DATETIME | no |  |
| `status` | VARCHAR(24) | no |  |

## `assignment` (app)

LEARN: a course for a caregiver: trigger, who made it required, due date, progress and score (private to the caregiver).

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `id` | INTEGER | no | primary |
| `caregiver_id` | VARCHAR(48) | no |  |
| `course_id` | VARCHAR(32) | no |  |
| `trigger` | VARCHAR(64) | no |  |
| `required_by` | VARCHAR(24) | yes |  |
| `confirmed_by` | VARCHAR(48) | yes |  |
| `due_date` | DATE | yes |  |
| `lessons_done` | JSON | no |  |
| `completed_at` | DATETIME | yes |  |
| `score` | FLOAT | yes |  |
| `status` | VARCHAR(24) | no |  |

## `audit_log` (app)

Append-only record of every decision, status change, confirmation and check-in: who, when, before, after, why.

| Column | Type | Null | Key |
| --- | --- | --- | --- |
| `id` | INTEGER | no | primary |
| `at` | DATETIME | no |  |
| `user_id` | VARCHAR(48) | no |  |
| `role` | VARCHAR(24) | no |  |
| `action` | VARCHAR(48) | no |  |
| `entity` | VARCHAR(32) | no |  |
| `entity_id` | VARCHAR(64) | no |  |
| `before` | JSON | yes |  |
| `after` | JSON | yes |  |
| `reason` | TEXT | yes |  |
