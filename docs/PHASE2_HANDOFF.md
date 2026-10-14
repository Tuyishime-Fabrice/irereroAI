# Phase 2 handoff

Phase 1 is a working platform running on simulated data, inside real Gicumbi boundaries. Phase 2
replaces the simulated data with official and partner sources and the baselines with fitted
models, without changing the screens or the API.

Each source is already specified: what files it expects, which tables it writes, and which
checks must pass before it loads. The full list, generated from the code, is in
[PHASE2_SOURCES.md](PHASE2_SOURCES.md).

## Ground rules that do not change

- **Never present simulated data as real.** Every row keeps its `origin`. The SIMULATED DATA
  label disappears only when nothing on screen comes from a `simulated` row.
- **Raw files never enter git.** They go in `data/raw/<adapter name>/`. NISR and DHS licences
  forbid redistribution.
- **Counts and areas only.** An adapter aggregates to sector, district or centre before writing.
- **Ranges, not points.** Every estimate is written with `low`, `estimate` and `high`. A source
  without a design-based interval gets a documented approximate one.
- **The demo generator never touches real data.** It refuses to run once any `official` or
  `partner` pipeline run exists. Use a separate database for demos.

## Implementing an adapter

Each adapter in `pipelines/adapters/` is a `PlannedAdapter` with a complete `spec`. To implement
one, subclass `SourceAdapter` and fill in the four steps:

1. `extract(raw_dir)`: read the expected files and parse them, with no other changes.
2. `validate(raw)`: return one `CheckResult` per entry in `spec.checks`. If any fails, nothing
   loads and the run is recorded as failed, with its results.
3. `align_to_sector(raw, conn)`: map records to `admin_unit.code` (or centre codes), keeping
   intervals and sample sizes. Join on `nisr_code` once the boundaries adapter has filled it.
4. `load(aligned, conn, run_id)`: write to `spec.target_tables`, with `origin`,
   `source`, `reference_year` and `pipeline_run_id` on every row. Return the rows written per
   table.

`run_adapter(adapter, engine)` wraps the steps in one `pipeline_run` row. That row records a
SHA-256 for every input file, the code version and the check results. All rows commit together
or not at all. The run appears on `/methodology`, `/national/status` and `/admin/pipelines`.

Add tests next to `pipelines/tests/test_registry.py` that use small synthetic fixtures (never
real microdata), and update the spec if the checks change. Then run
`python -m pipelines.registry --write`, because CI fails when PHASE2_SOURCES.md is stale.

### Suggested order

1. **`boundaries`**: official codes for every existing district and sector, plus cells and
   villages. Unmatched names go to a review list instead of being guessed. Everything else joins
   on these codes.
2. **`census_2022`** and **`worldpop`**: children aged 0–2 and 3–6 per sector and per 100 m
   cell. These replace the simulated demand points.
3. **`rdhs_2025`**, **`rdhs_2019_gps`**, **`eicv7`** and **`lfs_2025`**: inputs to sector-level
   stunting risk, poverty and the childcare barrier. RDHS gives district direct estimates; sector
   values come from the small-area model below.
4. **`ncda_mapping`**: real centres and reports, as `partner` data under an agreement with NCDA.
5. **`osm`** and **`education_yearbook`**: walking network and candidate school sites.

## Replacing the baselines

The API only sees the engine's interfaces (see [ARCHITECTURE.md](ARCHITECTURE.md)). To replace a
baseline:

| Interface | Phase 2 work | Keep |
| --- | --- | --- |
| `NeedEstimator` | Fit a small-area model (for example Fay–Herriot with census and WorldPop covariates) and write sector estimates with intervals to `need_estimate`. `StoredNeedEstimator` already reads them. | Intervals carried through to impact ranges |
| `CoverageModel` | Walking-time catchments over the OSM network. | The `reachable` / `assign` contract and the 30-minute default |
| `SiteOptimizer` | Optional exact solver (integer programming) behind `plan()`. | Rejected sites stay excluded; drivers are explained in the same terms |
| `EarlyWarning` | A learned model, evaluated against the rules on held-out weeks. Write its metrics to `model_version.metrics`. | Alerts name the numbers that triggered them |
| `AssistantProvider` | A language-model provider in `make_assistant`, enabled by `LLM_API_KEY`. | It answers only from the records passed in and names their tables |

Give every new implementation its own `version` string so suggestions stay traceable, and run it
next to the baseline on the same inputs before switching over.

## Known Phase 1 limits

- Centres, reports, need estimates, costs, candidate sites and parent requests are all simulated.
  Only the province, district and sector boundaries and the published figures on the landing
  page are real.
- Catchments are straight-line distance.
- No SMS gateway: one-time codes show on screen in demo mode, and the SMS report format runs in a
  simulator.
- Expired one-time codes and tokens are not purged on a schedule (see [PRIVACY.md](PRIVACY.md)).
- Kinyarwanda strings are unreviewed drafts. [i18n-review.md](i18n-review.md) lists every string
  waiting for a native-speaker review; reviewed keys go in `apps/web/messages/rw-reviewed.json`.
