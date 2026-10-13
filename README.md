# IrereroAI

Decision support for early childhood development (ECD) in Rwanda: plan where ECD centres are
needed, track weekly centre reports, help parents find verified centres, and learn from every
human decision. Built for the NISR 2026 Big Data Hackathon, Track 3.

AI suggests, humans decide. Every suggestion shows its reasons, a range and its sources, and
nothing executes without a person approving it.

## Run locally

Requirements: Docker with Compose.

```sh
docker compose up --build -d
make seed       # downloads boundaries, then builds the simulated Gicumbi demo
```

API: <http://localhost:8000/docs> · Web: <http://localhost:3000>

### Development without Docker

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 22 with pnpm, PostgreSQL 16
with PostGIS.

```sh
make setup      # dependencies and git hooks
make migrate
make seed-local
make api        # http://localhost:8000
make web        # http://localhost:3000
```

## Repository

| Path | Contents |
| --- | --- |
| `apps/api` | FastAPI service |
| `apps/web` | Next.js web app |
| `packages/contract` | Data contract: tables, record models, code lists |
| `packages/engine` | Explainable decision-support baselines |
| `pipelines` | Ingestion adapters and the demo data generator |
| `data` | Gitignored except the README and JSON Schemas |

## Team

Contact: fabricetuyishime2050@gmail.com

All rights reserved. This repository is private.
