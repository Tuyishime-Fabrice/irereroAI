.PHONY: setup migrate api web seed seed-local lint typecheck test

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
