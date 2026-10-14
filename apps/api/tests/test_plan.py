from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from .conftest import Headers

SCENARIO = {
    "district_code": "D-GICUMBI",
    "name": "Test plan",
    "budget_rwf": 120_000_000,
    "weights": {"stunting": 0.4, "readiness": 0.4, "jobs": 0.2},
}


def test_plan_reject_needs_reason_and_reruns_without_the_site(
    client: TestClient, planner: Headers, demo_engine: Engine
) -> None:
    created = client.post("/scenarios", json=SCENARIO, headers=planner)
    assert created.status_code == 201
    plan = created.json()
    assert "simulated" in plan["provenance"]["origins"]
    scenario = plan["data"]
    assert scenario["outcomes"]["cost_rwf"] <= SCENARIO["budget_rwf"]
    build = next(r for r in scenario["recommendations"] if r["action"] == "build")
    for rec in scenario["recommendations"]:
        assert rec["drivers"] is not None and rec["sources"]
        reached = rec["children_reached"]
        assert reached["low"] <= reached["estimate"] <= reached["high"]
        text_en = rec["explanation_en"].lower()
        assert "reduc" not in text_en and "lower stunting" not in text_en

    no_reason = client.post(
        f"/recommendations/{build['id']}/decision", json={"verdict": "reject"}, headers=planner
    )
    assert no_reason.status_code == 422

    rejected = client.post(
        f"/recommendations/{build['id']}/decision",
        json={"verdict": "reject", "reason_code": "no_land"},
        headers=planner,
    ).json()["data"]
    assert build["site_id"] not in {r["site_id"] for r in rejected["recommendations"]}
    assert rejected["rejected"][0]["site_id"] == build["site_id"]

    with demo_engine.connect() as conn:
        logged = conn.execute(
            text(
                "SELECT count(*) FROM audit_log WHERE action = 'recommendation.reject' "
                "AND entity_id = :id"
            ),
            {"id": build["id"]},
        ).scalar_one()
    assert logged == 1


def test_simulator_reports_countable_outcomes_only(client: TestClient, planner: Headers) -> None:
    body = {
        "district_code": "D-GICUMBI",
        "budget_rwf": 60_000_000,
        "weights": {"stunting": 1, "readiness": 0, "jobs": 0},
        "include_baseline": True,
    }
    result = client.post("/simulate", json=body, headers=planner).json()
    assert set(result["outcomes"]) == {
        "children_reached",
        "uncovered_remaining",
        "high_risk_reached",
        "mothers_under3_reached",
        "children_supported",
        "cost_rwf",
        "actions",
    }
    assert result["baseline"] is not None
