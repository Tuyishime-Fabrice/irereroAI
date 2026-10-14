# Deployment

The stack is three parts: PostgreSQL 16 with PostGIS 3.4, the FastAPI service and the Next.js web
app. Only the web app talks to the API, through its same-origin proxy, so the API can stay on a
private network.

For a judged demo, `docker compose` on one machine is enough (see the README). For a hosted demo,
use the setup below.

## Hosted demo: Vercel, a container host and managed PostGIS

### 1. Database

Any managed PostgreSQL 16 that offers the `postgis` extension works. The first migration runs
`CREATE EXTENSION IF NOT EXISTS postgis`, so the migration user needs permission to create
extensions (or an admin enables PostGIS beforehand).

For real personal data, the database must be hosted in Rwanda, or the storage approved by NCSA
(see [PRIVACY.md](PRIVACY.md)). Simulated demo data has no such constraint.

### 2. API

Build `apps/api/Dockerfile` from the repository root and run it on any container host. On start,
the container runs `alembic upgrade head` and then serves on port 8000.

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://USER:PASSWORD@HOST:5432/DB` (add `?sslmode=require` for managed hosts) <!-- pragma: allowlist secret --> |
| `JWT_SECRET` | A long random string (for example `openssl rand -hex 32`). Required when demo mode is off. Rotating it signs everyone out. |
| `DEMO_MODE` | `true` for the judged demo. It shows demo accounts and one-time codes, and fixes the calendar to the seeded weeks. Must be `false` anywhere real people sign in. |
| `CORS_ORIGINS` | Leave as is. The browser never calls the API directly. |

Health check: `GET /health`.

Seed the demo data once, from a machine that can reach the database:

```sh
DATABASE_URL=... uv run python -m pipelines.demo.generate
```

The generator drops and recreates every table. It refuses to run if the database holds any
official or partner data, but point it only at a demo database.

### 3. Web app on Vercel

1. Import the repository and set **Root Directory** to `apps/web`. Vercel detects Next.js and
   pnpm from the workspace lockfile.
2. Set the environment variables:

| Variable | Value |
| --- | --- |
| `API_INTERNAL_URL` | The API's base URL, for example `https://irerero-api.example.org` |
| `NEXT_PUBLIC_MAP_STYLE_URL` | Optional. A MapLibre style URL for a basemap. Without it, maps show boundaries only, which is also the offline fallback. |

Do not set `INSECURE_COOKIES` on any https deployment: it turns off the Secure flag on session
cookies and exists only for plain-http local runs. `NEXT_PUBLIC_DESIGN_PAGE` exposes the `/design`
component catalogue and should stay unset.

The build copies the MapLibre worker into `public/` (`prebuild`), so no extra step is needed.

### 4. Check

- `/find`, after choosing a sector, shows centres with the SIMULATED DATA label, and
  `/methodology` lists the `demo_generator` run.
- `/sign-in` lists the demo accounts (demo mode only). `/tour` runs end to end.
- Optionally, run the Playwright suite against the deployment. It changes data (it sends a report,
  rejects a suggestion and resolves an alert), so reseed afterwards:

```sh
E2E_BASE_URL=https://your-app.vercel.app pnpm --filter web e2e
```

## Turning demo mode off

1. Use a fresh database. Never one that held the demo.
2. Set `DEMO_MODE=false` and a strong `JWT_SECRET`. The API refuses to start without one.
3. Create the first admin account directly in the database, with an Argon2id password hash and a
   TOTP secret. The admin then creates every other account at `/admin`.
4. Load sources through the Phase 2 adapters ([PHASE2_HANDOFF.md](PHASE2_HANDOFF.md)).
5. Work through the go-live list in [PRIVACY.md](PRIVACY.md).
