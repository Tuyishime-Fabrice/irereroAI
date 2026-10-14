"""The API is the guard: a planner reads the national overview and plans only their district."""

import pytest
from fastapi.testclient import TestClient

from .conftest import Headers


@pytest.mark.parametrize(
    "path",
    [
        "/geo/areas?parent=D-GICUMBI",
        "/geo/centres",
        "/geo/demand",
        "/national/districts",
        "/scenarios?district=D-GICUMBI",
    ],
)
def test_planner_endpoints_need_a_session(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


def test_planner_reads_the_national_map_at_district_level(
    client: TestClient, planner: Headers
) -> None:
    national = client.get("/geo/areas?parent=RW&level=district", headers=planner)
    assert national.status_code == 200
    assert len(national.json()["data"]["features"]) == 30
    assert client.get("/national/districts", headers=planner).status_code == 200


def test_planner_is_limited_to_their_district(client: TestClient, planner: Headers) -> None:
    assert client.get("/geo/areas?parent=D-GICUMBI", headers=planner).status_code == 200
    assert client.get("/geo/areas?parent=D-RULINDO", headers=planner).status_code == 403
    assert client.get("/geo/areas?parent=RW&level=sector", headers=planner).status_code == 403
    assert client.get("/geo/centres?area=D-RULINDO", headers=planner).status_code == 403
    assert client.get("/decisions?district=D-RULINDO", headers=planner).status_code == 403
    body = {
        "district_code": "D-RULINDO",
        "name": "x",
        "budget_rwf": 1_000_000,
        "weights": {"stunting": 1, "readiness": 0, "jobs": 0},
    }
    assert client.post("/scenarios", json=body, headers=planner).status_code == 403
