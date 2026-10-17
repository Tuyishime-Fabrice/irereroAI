"""Shared fixtures. Database tests run against DATABASE_URL, rebuilt once per session."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from pipelines.build import build
from pipelines.db import engine as make_engine


@pytest.fixture(scope="session")
def demo_engine() -> Iterator[Engine]:
    engine = make_engine()
    build(engine)
    yield engine
    engine.dispose()
