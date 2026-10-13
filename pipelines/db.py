import os

from sqlalchemy import Engine, create_engine

# Local development default only; deployments set DATABASE_URL.
DEFAULT_URL = (
    "postgresql+psycopg://irerero:irerero@localhost:5432/irerero"  # pragma: allowlist secret
)


def engine() -> Engine:
    return create_engine(os.environ.get("DATABASE_URL", DEFAULT_URL))
