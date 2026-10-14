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


def test_nearby_shows_only_verified_centres_without_small_counts(
    client: TestClient, demo_engine: Engine
) -> None:
    centres = client.get("/public/nearby?lon=30.07&lat=-1.58&limit=10").json()["data"]
    with demo_engine.connect() as conn:
        verified = set(conn.execute(text("SELECT code FROM centre WHERE verified")).scalars())
    assert centres and {c["code"] for c in centres} <= verified
    for centre in centres:
        free = centre["free_places"]
        assert free["suppressed"] or free["value"] == 0 or free["value"] >= 5


def test_no_personal_data_is_kept_about_parents(demo_engine: Engine) -> None:
    with demo_engine.connect() as conn:
        columns = set(
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'demand_signal'"
                )
            ).scalars()
        )
    assert columns == {
        "id",
        "grid_cell",
        "cell_centre",
        "sector_code",
        "age_band",
        "origin",
        "created_at",
    }


def test_audit_log_cannot_be_rewritten(demo_engine: Engine) -> None:
    import pytest
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError), demo_engine.begin() as conn:
        conn.execute(text("DELETE FROM audit_log"))
