# Architecture

IrereroAI is one repository with a Python side (API, data contract, engine, pipelines) and a
TypeScript side (the web app). Data flows one way: sources → pipelines → contract tables →
engine → API → web. People's decisions flow back in through the API and are kept in the audit log
and the decisions tables, which the next plan run reads.

```
            data/raw/ (gitignored)             geoBoundaries (CC BY 4.0)
                   │                                    │
                   ▼                                    ▼
        pipelines/adapters/*  (Phase 2)      pipelines/demo  (Phase 1, simulated)
                   └──────────────┬─────────────────────┘
                                  ▼  every load is one pipeline_run with file checksums and checks
                PostgreSQL 16 + PostGIS   ◄── tables defined in packages/contract
                                  │
                 apps/api (FastAPI) ── packages/engine (pure Python, no database access)
                                  │  JSON with provenance, JWT, role and scope checks
                 apps/web (Next.js) ── /api/[...path] same-origin proxy, httpOnly cookies
                                  │
                       browser (desktop, phone, PWA offline queue)
```

## Packages

| Path | Role | Depends on |
| --- | --- | --- |
| `packages/contract` | SQLAlchemy tables, code lists, shared validation, the 500 m grid, password hashing. The single source of truth for the data model. | SQLAlchemy, GeoAlchemy2 |
| `packages/engine` | Decision-support baselines behind stable interfaces. Takes plain dataclasses, returns plain dataclasses. | nothing in the repo |
| `pipelines` | Source adapters (Phase 2 specs), the run recorder, and the deterministic demo generator. | contract, engine |
| `apps/api` | FastAPI service: auth, role and scope checks, services that load contract rows into engine types, routes, audit. | contract, engine |
| `apps/web` | Next.js App Router app for all six roles, English and Kinyarwanda. | the API's OpenAPI document |

The engine has no database code on purpose. `apps/api/src/irerero_api/engine_io` converts rows
to engine inputs, so a Phase 2 model can be tested on fixtures without a database, and swapped
without touching routes.

## Data contract

Tables live in `packages/contract/src/irerero_contract/tables`. Every column has a comment;
`python -m irerero_contract.export` writes those to JSON Schemas in `data/contract/` and to
[DATA_CONTRACT.md](DATA_CONTRACT.md). CI fails if either is stale, and `alembic check` fails if a
migration is missing.

Every fact table carries provenance: `source`, `reference_year`, `origin` (`official`,
`public`, `partner` or `simulated`) and `pipeline_run_id`. Estimates carry `low`, `estimate` and
`high`, never a bare number.

Admin units keep stable internal codes (`D-GICUMBI`, `S-GICUMBI-BYUMBA`) and a nullable
`nisr_code`, which the Phase 2 boundaries adapter fills, so loaded data and saved decisions
survive the switch to official codes.

## Engine interfaces

| Interface | Phase 1 implementation | What Phase 2 changes |
| --- | --- | --- |
| `NeedEstimator` | `StoredNeedEstimator` reads area estimates the pipelines wrote. | Small-area estimates from census, EICV7, RDHS and WorldPop. |
| `CoverageModel` | `StraightLineCoverage`: 30 minutes at 67 m/min, nearest centres fill first. | Walking time over the OSM network. |
| `SiteOptimizer` | `GreedyOptimizer`: best weighted benefit per franc within budget, honouring rejected sites. `largest_population_first` is the comparison baseline. | An exact solver can implement the same `plan()`. |
| `EarlyWarning` | `RuleBasedEarlyWarning`: each centre against its own history. | A learned model, evaluated against these rules. |
| `Explainer` | `TemplateExplainer`: English and Kinyarwanda from drivers and numbers. | — |
| `AssistantProvider` | `TemplateAssistant`, chosen by `make_assistant`. Answers only from records it is given and names their tables. | A language-model provider behind `LLM_API_KEY`, same inputs and citations. |

Each implementation has a `version` that is written to `model_version` and shown on the national
status page, so every suggestion can be traced to the model that made it.

## API

- **Envelope.** Data responses are `{data, provenance}`; `provenance` lists the origins and
  sources behind the data. The web app shows the SIMULATED DATA label whenever any origin on
  screen is `simulated`.
- **Auth.** Short-lived JWT access tokens and rotating refresh tokens (stored server-side, revoked
  on rotation and sign-out). Staff sign in with email and password, and admins also with TOTP.
  Caregivers use phone and centre code; parents get a one-time code by SMS (shown on screen in demo
  mode only).
- **Access.** Every route declares its roles (`require_roles`). Routes that take a centre or area
  also resolve it up the sector → district chain and refuse anything outside the user's scope
  (`require_centre`, `require_area`). The web app hides what a role cannot use, but the API is the
  guard; `apps/api/tests/test_rbac.py` proves it.
- **Audit.** Every human decision (verdicts on suggestions, plan runs, alert follow-up,
  verifications, account and default changes) writes an `audit_log` row. Database triggers reject
  `UPDATE`, `DELETE` and `TRUNCATE` on that table.
- **Typed client.** `python -m irerero_api.openapi_export` writes `apps/web/openapi.json`;
  `pnpm --filter web generate:api` turns it into TypeScript types. CI fails on drift.

## Web

- **Proxy.** The browser calls `/api/...` on its own origin. `src/app/api/[...path]/route.ts`
  forwards to the API with the access token from an httpOnly cookie and refreshes it once on
  expiry. Tokens never reach client JavaScript. Server components call the API directly with the
  same cookie (`src/lib/api/server.ts`).
- **Language.** next-intl with a cookie-chosen locale. Every Kinyarwanda string is a draft until
  reviewed; [i18n-review.md](i18n-review.md) lists them and the UI marks draft translations.
- **Maps.** MapLibre loads on demand. Without a basemap it falls back to boundaries only, so the
  demo works offline. Every map has a table alternative.
- **Offline.** The caregiver report is an installable PWA. Unsent reports wait in IndexedDB and
  send when the phone reconnects.
- **Tour.** `/tour` walks the pitch in eight steps, switching demo accounts as it goes.

## Testing

| Layer | Where | Runs in CI |
| --- | --- | --- |
| Contract, engine, pipelines, API (including role and scope checks and privacy rules) | `pytest` | python job, against PostGIS |
| Web units (number formatting, map classes, report steps, colour contrast, message parity) | `vitest` | web job |
| Demo journeys and WCAG 2.1 AA (axe) in both languages | `apps/web/e2e` (Playwright) | docker job, against the compose stack |
