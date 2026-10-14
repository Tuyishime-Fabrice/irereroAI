.PHONY: setup migrate api web seed seed-local lint typecheck test e2e client

setup:  ## Install all dependencies and git hooks
	uv sync
	pnpm install
	uv run pre-commit install

migrate:  ## Apply database migrations (local)
	cd apps/api && uv run alembic upgrade head

api:  ## Run the API with reload (local)
	cd apps/api && uv run uvicorn irerero_api.main:app --reload --port 8000

web:  ## Run the web app in dev mode (local)
	pnpm --filter web dev

seed:  ## Seed simulated demo data into the docker compose database
	docker compose exec -T api python -m pipelines.demo.generate

seed-local:  ## Seed simulated demo data into the local database
	uv run python -m pipelines.demo.generate

lint:
	uv run ruff check .
	uv run ruff format --check .
	pnpm --filter web lint

typecheck:
	uv run mypy
	pnpm --filter web typecheck

test:
	uv run pytest
	pnpm --filter web test

e2e:  ## Demo journeys and accessibility checks against a running, freshly seeded stack
	pnpm --filter web e2e

client:  ## Regenerate the web app's API types from the OpenAPI schema
	uv run python -m irerero_api.openapi_export apps/web/openapi.json
	pnpm --filter web generate:api
	uv run python -m irerero_contract.export
