from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from .conftest import Login

CURRENT_WEEK = "2026-09-21"


def report(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "centre_code": "ECD-GIC-001",
        "week_start": CURRENT_WEEK,
        "enrolled_0_2_female": 6,
        "enrolled_0_2_male": 5,
        "enrolled_3_6_female": 15,
        "enrolled_3_6_male": 14,
        "avg_daily_attendance": 34,
        "waiting_list": 2,
        "caregivers_present": 3,
        "days_open": 5,
        "days_meal_served": 5,
        "wash_available": True,
        "referrals_growth_monitoring": 1,
        "children_with_disability": 1,
        "main_problem": "none",
        "channel": "web",
    }
    return body | changes


def test_attendance_above_enrolment_is_refused_in_plain_codes(
    client: TestClient, auth: Login
) -> None:
    response = client.post(
        "/reports/check", json=report(avg_daily_attendance=80), headers=auth("caregiver")
    )
    assert response.json()["errors"][0]["code"] == "attendance_above_enrolment"


def test_unusual_values_need_confirmation(client: TestClient, auth: Login) -> None:
    body = report(enrolled_3_6_female=60, enrolled_3_6_male=60, avg_daily_attendance=100)
    unconfirmed = client.post("/reports/check", json=body, headers=auth("caregiver")).json()
    assert not unconfirmed["accepted"]
    assert unconfirmed["warnings"]
    confirmed = client.post(
        "/reports/check", json=body | {"confirmed": True}, headers=auth("caregiver")
    ).json()
    assert confirmed["accepted"]
    assert "out_of_range_confirmed" in confirmed["flags"]


def test_caregiver_submits_this_weeks_report_once(
    client: TestClient, auth: Login, demo_engine: Engine
) -> None:
    caregiver = auth("caregiver")
    assert client.post("/reports", json=report(), headers=caregiver).status_code == 201
    assert client.post("/reports", json=report(), headers=caregiver).status_code == 409
    home = client.get("/centres/ECD-GIC-001", headers=caregiver).json()["data"]
    assert home["reported_this_week"]
    with demo_engine.connect() as conn:
        origin = conn.execute(
            text(
                "SELECT origin FROM weekly_report WHERE centre_code = 'ECD-GIC-001' "
                "AND week_start = :w"
            ),
            {"w": CURRENT_WEEK},
        ).scalar_one()
    assert origin == "simulated"


def test_caregiver_cannot_report_for_another_centre(client: TestClient, auth: Login) -> None:
    response = client.post(
        "/reports", json=report(centre_code="ECD-GIC-002"), headers=auth("caregiver")
    )
    assert response.status_code == 403


def test_sms_report_parses_and_explains_format_errors(client: TestClient, auth: Login) -> None:
    caregiver = auth("caregiver")
    bad = client.post("/sms/simulate", json={"text": "IR ECD-GIC-001 39 1 2"}, headers=caregiver)
    assert bad.json() == {
        "status": "format_error",
        "format_error": "wrong_count",
        "format_detail": "4 of 15",
        "parsed": None,
        "validation": None,
    }
    text_ = "IR ECD-GIC-001 38 6 5 12 13 50 2 2 5 5 Y 1 1 0"
    result = client.post("/sms/simulate", json={"text": text_}, headers=caregiver).json()
    assert result["status"] in {"rejected", "duplicate"}
    if result["status"] == "rejected":
        assert result["validation"]["errors"][0]["code"] == "attendance_above_enrolment"


def test_new_no_water_report_raises_an_alert(
    client: TestClient, auth: Login, demo_engine: Engine
) -> None:
    """An officer enters the week-12 report of the stopped centre: no water, children away."""
    officer_free_centre = "ECD-GIC-004"  # Rukomo: outside the demo officer's sector
    with demo_engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE user_account SET scope_code = 'S-GICUMBI-RUKOMO' "
                "WHERE email = 'officer.byumba@demo.irereroai.rw'"
            )
        )
    try:
        token = client.post("/demo/login/sector_officer").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        body = report(
            centre_code=officer_free_centre,
            enrolled_0_2_female=2,
            enrolled_0_2_male=2,
            enrolled_3_6_female=6,
            enrolled_3_6_male=6,
            avg_daily_attendance=10,
            caregivers_present=1,
            wash_available=False,
            main_problem="no_water",
            channel="assisted",
        )
        assert client.post("/reports", json=body, headers=headers).status_code == 201
        alerts = client.get("/alerts?area=S-GICUMBI-RUKOMO", headers=headers).json()["data"]
        assert "wash" in {a["kind"] for a in alerts if a["centre_code"] == officer_free_centre}
    finally:
        with demo_engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE user_account SET scope_code = 'S-GICUMBI-BYUMBA' "
                    "WHERE email = 'officer.byumba@demo.irereroai.rw'"
                )
            )
