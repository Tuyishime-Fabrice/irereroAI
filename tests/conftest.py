"""One build from the demo bundle into a throwaway database, shared by the data tests."""

from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine

from irerero.db.models import Base
from irerero.pipeline.build import build
from irerero.pipeline.inputs import Inputs, load_inputs


@pytest.fixture(scope="session")
def empty_raw(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A data/raw/ with nothing in it, so every loader takes the demo path."""
    return tmp_path_factory.mktemp("raw")


@pytest.fixture(scope="session")
def eng(tmp_path_factory: pytest.TempPathFactory) -> Engine:
    path = tmp_path_factory.mktemp("db") / "test.sqlite"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def inputs(empty_raw: Path) -> Inputs:
    return load_inputs(empty_raw)


@pytest.fixture(scope="session")
def tables(empty_raw: Path, eng: Engine, tmp_path_factory: pytest.TempPathFactory) -> dict:
    return build(empty_raw, eng, tmp_path_factory.mktemp("processed"))
