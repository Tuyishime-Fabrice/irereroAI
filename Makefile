.DEFAULT_GOAL := help
.PHONY: help install sources data test lint format app check

help:  ## List the targets
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

install:  ## Install Python 3.11 dependencies (with the OSM road-network extra)
	uv sync --extra osm

sources:  ## Create the data/raw/ folders and list which source files are present
	uv run python -m irerero.data

data:  ## Rebuild every analysis table from data/raw/, demo data where files are missing
	uv run python -m irerero.pipeline.build

test:  ## Run the test suite
	uv run pytest

lint:  ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .

format:  ## Fix lint and formatting
	uv run ruff check --fix .
	uv run ruff format .

app:  ## Run the Streamlit app
	uv run streamlit run app/Home.py

check: lint test  ## Everything CI runs
	uv run python -m irerero.data --check
