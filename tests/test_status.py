"""Each part of a screen keeps the status of what it rests on: a real estimate does not make
a distance layer built on simulated schools, or a diagnosis built on a simulated yearbook,
look real."""

import pandas as pd

from irerero.config import MODEL, PUBLISHED, SIMULATED
from irerero.diagnose.features import simulated_features
from irerero.plan.frame import distance_status, status_of

REAL_ESTIMATE = pd.DataFrame(
    {"status": [MODEL, MODEL], "distance_method": ["straight line (indicative)"] * 2}
)


def _obs(**statuses: str) -> pd.DataFrame:
    return pd.DataFrame({"source_id": list(statuses), "status": list(statuses.values())})


def test_a_table_is_simulated_when_any_row_is():
    assert status_of(REAL_ESTIMATE) == MODEL
    assert status_of(REAL_ESTIMATE.assign(status=[MODEL, SIMULATED])) == SIMULATED
    assert status_of(pd.DataFrame()) == MODEL


def test_distance_follows_the_school_points_not_the_estimate():
    assert distance_status(REAL_ESTIMATE) == MODEL
    simulated_schools = REAL_ESTIMATE.assign(
        distance_method="straight line (indicative), simulated schools"
    )
    assert distance_status(simulated_schools) == SIMULATED


def test_simulated_indicators_are_named_by_their_source():
    obs = _obs(census_2022=MODEL, eicv7=PUBLISHED, yearbook=SIMULATED, rdhs_2025=SIMULATED)
    found = simulated_features(obs, REAL_ESTIMATE)
    assert {"pupils_per_teacher", "qualified_share", "stunting"} <= found
    assert not {"attendance_2022", "poverty", "far_share", "nonattendance"} & found
    schools = REAL_ESTIMATE.assign(distance_method="road, simulated schools")
    assert "far_share" in simulated_features(obs, schools)
    everything = REAL_ESTIMATE.assign(status=SIMULATED)
    assert {"nonattendance", "far_share"} <= simulated_features(_obs(census_2022=MODEL), everything)
    assert simulated_features(_obs(census_2022=MODEL, eicv7=PUBLISHED), REAL_ESTIMATE) == set()


def test_the_demo_peer_model_and_diagnosis_say_simulated(tables):
    """In the demo everything rests on stand-ins, so both stay simulated."""
    assert set(tables["model_output"].status) == {SIMULATED}
    assert set(tables["diagnosis"].status) == {SIMULATED}
