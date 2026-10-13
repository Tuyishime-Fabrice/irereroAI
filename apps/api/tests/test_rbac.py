"""The API is the guard: each role reaches only its own scope."""

import pytest
from fastapi.testclient import TestClient

from .conftest import Login


def test_sector_officer_cannot_read_another_sector(client: TestClient, auth: Login) -> None:
    officer = auth("sector_officer")  # Byumba
    assert client.get("/centres?area=S-GICUMBI-BYUMBA", headers=officer).status_code == 200
    assert client.get("/centres?area=S-GICUMBI-RUKOMO", headers=officer).status_code == 403
    assert client.get("/centres/ECD-GIC-004", headers=officer).status_code == 403
    assert client.get("/alerts?area=S-GICUMBI-RUKOMO", headers=officer).status_code == 403
    assert client.get("/reports?centre_code=ECD-GIC-004", headers=officer).status_code == 403


def test_sector_officer_sees_only_own_sector_alerts(client: TestClient, auth: Login) -> None:
    alerts = client.get("/alerts", headers=auth("sector_officer")).json()["data"]
    assert alerts
    assert {a["sector_code"] for a in alerts} == {"S-GICUMBI-BYUMBA"}


def test_caregiver_cannot_read_another_centre(client: TestClient, auth: Login) -> None:
    caregiver = auth("caregiver")  # ECD-GIC-001
    assert client.get("/centres/ECD-GIC-001", headers=caregiver).status_code == 200
    assert client.get("/centres/ECD-GIC-002", headers=caregiver).status_code == 403
    assert client.get("/reports?centre_code=ECD-GIC-002", headers=caregiver).status_code == 403
    alerts = client.get("/alerts", headers=caregiver).json()["data"]
    assert all(a["centre_code"] == "ECD-GIC-001" for a in alerts)


def test_planner_is_limited_to_their_district(client: TestClient, auth: Login) -> None:
    planner = auth("district_planner")
    assert client.get("/geo/areas?parent=D-GICUMBI", headers=planner).status_code == 200
    assert client.get("/geo/areas?parent=D-RULINDO", headers=planner).status_code == 403
    body = {
        "district_code": "D-RULINDO",
        "name": "x",
        "budget_rwf": 1_000_000,
        "weights": {"stunting": 1, "readiness": 0, "jobs": 0},
    }
    assert client.post("/scenarios", json=body, headers=planner).status_code == 403


@pytest.mark.parametrize(
    ("role", "path", "expected"),
    [
        ("district_planner", "/national/districts", 403),
        ("sector_officer", "/national/districts", 403),
        ("national_analyst", "/national/districts", 200),
        ("national_analyst", "/admin/users", 403),
        ("district_planner", "/admin/audit", 403),
        ("admin", "/admin/audit", 200),
        ("caregiver", "/geo/areas?parent=D-GICUMBI", 403),
        ("parent", "/centres", 403),
    ],
)
def test_role_gates(client: TestClient, auth: Login, role: str, path: str, expected: int) -> None:
    assert client.get(path, headers=auth(role)).status_code == expected


def test_only_officers_record_verification(client: TestClient, auth: Login) -> None:
    response = client.post("/centres/ECD-GIC-001/verify", json={}, headers=auth("district_planner"))
    assert response.status_code == 403
