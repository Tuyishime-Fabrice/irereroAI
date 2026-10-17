"""The checks the brief requires of the data layer, run on the demo bundle. The same checks run
on the real files once they are in data/raw/."""

import pandas as pd
import pytest

from irerero.config import STATUSES
from irerero.data.crosswalk import FILE as CROSSWALK
from irerero.data.sources import census

COUNT_COLUMNS = [c.name for c in census.COUNTS]


def test_sector_rows_sum_to_district_totals(inputs):
    sectors = inputs.census_sectors.frame
    districts = inputs.census_districts.frame.set_index("district_name")
    for column in COUNT_COLUMNS:
        if sectors[column].isna().all():
            continue
        sums = sectors.groupby("district_name")[column].sum()
        pd.testing.assert_series_equal(
            sums.sort_index(),
            districts[column].loc[sums.index].sort_index(),
            check_names=False,
            check_dtype=False,
        )


def test_attending_plus_never_attended_equals_total(inputs):
    for loaded in (inputs.census_sectors, inputs.census_districts):
        frame = loaded.frame
        assert (
            frame.children_3_5_attending + frame.children_3_5_never_attended == frame.children_3_5
        ).all()


def test_all_416_sectors_join_to_boundaries(inputs):
    boundary_ids = set(inputs.sectors.geo_id)
    census_ids = set(inputs.census_sectors.frame.geo_id)
    crosswalk_ids = set(pd.read_csv(CROSSWALK, dtype=str).geo_id)
    assert len(boundary_ids) == 416
    assert census_ids == boundary_ids
    assert crosswalk_ids == boundary_ids


def test_boundary_hierarchy(inputs):
    assert len(inputs.units["province"]) == 5
    assert len(inputs.units["district"]) == 30
    assert set(inputs.sectors.parent_id) <= set(inputs.districts.geo_id)
    assert set(inputs.districts.parent_id) <= set(inputs.units["province"].geo_id)
    assert inputs.sectors.groupby("parent_id").size().min() > 0


def test_no_duplicate_observation_keys(tables):
    obs = tables["observation"]
    key = ["geo_id", "indicator_id", "reference_period"]
    assert not obs.duplicated(key).any(), obs[obs.duplicated(key, keep=False)].head()


def test_every_observation_has_source_and_status(tables):
    obs = tables["observation"]
    assert obs.source_id.notna().all()
    assert obs.status.notna().all()
    assert set(obs.status) <= set(STATUSES)
    assert set(obs.source_id) <= set(tables["source"].source_id)
    assert set(obs.geo_id) <= set(tables["geo_unit"].geo_id)


def test_demo_values_are_marked_simulated(tables):
    """With nothing in data/raw/, every value is a simulated stand-in and says so."""
    assert set(tables["observation"].status) == {"simulated"}
    assert not tables["source"].query("source_id != 'geoboundaries'").loaded.any()


def test_tables_reach_the_database(tables, eng):
    from irerero.db.store import read

    assert len(read(eng, "observation")) == len(tables["observation"])
    assert len(read(eng, "geo_unit", level="sector")) == 416


@pytest.mark.parametrize("indicator", ["children_3_5", "attending_3_5", "pp_pupils"])
def test_key_indicators_present(tables, indicator):
    assert indicator in set(tables["observation"].indicator_id)
