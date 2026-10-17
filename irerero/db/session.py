"""One engine for the whole app. SQLite file by default; Postgres when DATABASE_URL is set, so
plans and LEARN progress survive app restarts when deployed."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from irerero.config import DATA
from irerero.db.models import Base

DEFAULT_URL = f"sqlite:///{DATA / 'irerero.sqlite'}"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    # Supabase and Neon hand out postgres:// URLs; SQLAlchemy wants the driver named.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


@lru_cache
def engine(url: str | None = None) -> Engine:
    url = url or database_url()
    eng = create_engine(url, pool_pre_ping=True)
    if url.startswith("sqlite"):

        @event.listens_for(eng, "connect")
        def _foreign_keys(dbapi_connection, _):  # type: ignore[no-untyped-def]
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


@contextmanager
def session(eng: Engine | None = None) -> Iterator[Session]:
    with Session(eng or engine()) as s:
        yield s
        s.commit()
