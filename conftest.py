"""Shared fixtures. Database tests run against DATABASE_URL, rebuilt once per session."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from pipelines.db import engine as make_engine
from pipelines.demo.generate import generate


@pytest.fixture(scope="session")
def demo_engine() -> Iterator[Engine]:
    engine = make_engine()
    generate(engine)
    yield engine
    engine.dispose()
