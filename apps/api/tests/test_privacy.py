from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from irerero_api.suppression import suppress, suppress_csv


def test_small_counts_are_suppressed() -> None:
    assert suppress(3).suppressed and suppress(3).value is None
    assert suppress(0).value == 0
    assert suppress(5).value == 5
    assert suppress_csv(4) == "<5"


def test_centre_request_stores_only_the_grid_cell(client: TestClient, demo_engine: Engine) -> None:
    lon, lat = 29.951234, -1.471234
    response = client.post("/public/demand", json={"lon": lon, "lat": lat})
    assert response.status_code == 201
    cell = response.json()["grid_cell"]
    with demo_engine.connect() as conn:
        stored = conn.execute(
            text(
                "SELECT ST_X(cell_centre), ST_Y(cell_centre) FROM demand_signal "
                "WHERE grid_cell = :c ORDER BY created_at DESC LIMIT 1"
            ),
            {"c": cell},
        ).one()
    assert (round(stored[0], 6), round(stored[1], 6)) != (lon, lat)
    assert abs(stored[0] - lon) < 0.005 and abs(stored[1] - lat) < 0.005


def test_empty_search_becomes_a_demand_signal(client: TestClient, demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM demand_signal")).scalar_one()
    result = client.get("/public/centres?lon=29.9&lat=-1.45&radius_km=1").json()["data"]
    assert result == {"centres": [], "demand_recorded": True}
    with demo_engine.connect() as conn:
        after = conn.execute(text("SELECT count(*) FROM demand_signal")).scalar_one()
    assert after == before + 1


def test_public_find_shows_only_verified_centres(client: TestClient, demo_engine: Engine) -> None:
    centres = client.get("/public/centres?lon=30.07&lat=-1.58&radius_km=30").json()["data"]
    with demo_engine.connect() as conn:
        verified = set(conn.execute(text("SELECT code FROM centre WHERE verified")).scalars())
    assert {c["code"] for c in centres["centres"]} <= verified


def test_parent_can_delete_their_account(client: TestClient) -> None:
    code = client.post("/auth/otp/request", json={"phone": "+250700000077"}).json()["demo_code"]
    token = client.post("/auth/otp/verify", json={"phone": "+250700000077", "code": code}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    saved = client.post(
        "/parent/searches", json={"label": "Home", "lon": 30.07, "lat": -1.58}, headers=headers
    )
    assert saved.status_code == 201
    assert client.delete("/parent/account", headers=headers).status_code == 204
    again = client.post("/auth/otp/request", json={"phone": "+250700000077"}).json()["demo_code"]
    fresh = client.post("/auth/otp/verify", json={"phone": "+250700000077", "code": again}).json()[
        "access_token"
    ]
    assert client.get("/parent/searches", headers={"Authorization": f"Bearer {fresh}"}).json() == []


def test_audit_log_cannot_be_rewritten(demo_engine: Engine) -> None:
    import pytest
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError), demo_engine.begin() as conn:
        conn.execute(text("DELETE FROM audit_log"))
