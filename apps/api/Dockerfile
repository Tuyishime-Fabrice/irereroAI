# Build context: repository root.
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY apps/api/pyproject.toml apps/api/
COPY packages/contract/pyproject.toml packages/contract/
COPY packages/engine/pyproject.toml packages/engine/
COPY pipelines/pyproject.toml pipelines/
RUN uv sync --frozen --no-dev --no-install-workspace

COPY apps/api apps/api
COPY packages packages
COPY pipelines pipelines
RUN uv sync --frozen --no-dev

RUN useradd --system --create-home app && mkdir -p data/raw && chown -R app data
USER app
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/apps/api
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn irerero_api.main:app --host 0.0.0.0 --port 8000"]
