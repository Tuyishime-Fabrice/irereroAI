from pathlib import Path

import pytest

import irerero_contract.tables  # noqa: F401
from irerero_contract.base import Base
from irerero_contract.indicators import INDICATORS
from pipelines.registry import ADAPTERS

PHASE2_SOURCES = {
    "census_2022",
    "eicv7",
    "rdhs_2025",
    "rdhs_2019_gps",
    "lfs_2025",
    "education_yearbook",
    "ncda_mapping",
    "worldpop",
    "osm",
    "boundaries",
}


def test_every_phase2_source_has_an_adapter() -> None:
    assert set(ADAPTERS) == PHASE2_SOURCES


@pytest.mark.parametrize("name", sorted(PHASE2_SOURCES))
def test_spec_is_complete_and_points_at_real_tables(name: str) -> None:
    spec = ADAPTERS[name].spec
    assert spec.expected_files and spec.checks and spec.target_tables
    assert set(spec.target_tables) <= set(Base.metadata.tables)
    assert set(spec.indicators) <= set(INDICATORS)
    for expected in spec.expected_files:
        assert expected.pattern.startswith(f"{name}/")


def test_planned_adapters_refuse_to_run(tmp_path: Path) -> None:
    adapter = ADAPTERS["census_2022"]()
    with pytest.raises(NotImplementedError, match="Phase 2"):
        adapter.extract(tmp_path)
