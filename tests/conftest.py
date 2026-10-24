"""One build from the demo bundle into a throwaway database, shared by the data tests."""

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine

# Before anything imports irerero.config: the app tests build through the app, which reads
# data/raw/ and writes data/processed/. Point both at empty folders so every test runs on the
# demo bundle, whatever real files this machine holds, and leaves its build alone.
_SCRATCH = Path(tempfile.mkdtemp(prefix="irerero-tests-"))
os.environ["IRERERO_RAW"] = str(_SCRATCH / "raw")
os.environ["IRERERO_PROCESSED"] = str(_SCRATCH / "processed")
(_SCRATCH / "raw").mkdir()

from irerero.db.models import Base  # noqa: E402
from irerero.pipeline.build import build  # noqa: E402
from irerero.pipeline.inputs import Inputs, load_inputs  # noqa: E402


@pytest.fixture(scope="session")
def empty_raw(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A data/raw/ with nothing in it, so every loader takes the demo path."""
    return tmp_path_factory.mktemp("raw")


@pytest.fixture(scope="session")
def build_eng(tmp_path_factory: pytest.TempPathFactory) -> Engine:
    path = tmp_path_factory.mktemp("db") / "test.sqlite"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def inputs(empty_raw: Path) -> Inputs:
    return load_inputs(empty_raw)


@pytest.fixture(scope="session")
def tables(empty_raw: Path, build_eng: Engine, tmp_path_factory: pytest.TempPathFactory) -> dict:
    return build(empty_raw, build_eng, tmp_path_factory.mktemp("processed"))
