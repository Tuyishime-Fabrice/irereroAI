"""Smoke test: every screen renders for every role that can see it, without an exception."""

import pytest
from streamlit.testing.v1 import AppTest

from irerero.config import ROOT
from irerero.ui.roles import DEMO_USERS

APP = str(ROOT / "app" / "streamlit_app.py")


@pytest.fixture(scope="module")
def built_db(tmp_path_factory, monkeypatch_module):
    """The app builds into its own database on first start, from the demo bundle."""
    path = tmp_path_factory.mktemp("appdb") / "app.sqlite"
    monkeypatch_module.setenv("DATABASE_URL", f"sqlite:///{path}")
    return path


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.mark.parametrize("user", DEMO_USERS, ids=lambda u: u.role)
def test_role_home_renders(built_db, user):
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = user
    at.run()
    assert not at.exception, [e.message for e in at.exception]


@pytest.mark.parametrize(
    "page",
    [
        "views/national.py",
        "views/priorities.py",
        "views/sector.py",
        "views/plan.py",
        "views/methods.py",
    ],
)
def test_planner_pages_render(built_db, page):
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    at.switch_page(page)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert any("ir-title" in m.value for m in at.markdown)  # the page header rendered


@pytest.mark.parametrize(
    "page",
    ["views/priorities.py", "views/sector.py", "views/plan.py", "views/brief.py"],
)
def test_analyst_pages_render(built_db, page):
    """Analysts pick any district; the district picker lives inside the page's filter panel."""
    analyst = next(u for u in DEMO_USERS if u.role == "national_analyst")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = analyst
    at.run()
    at.switch_page(page)
    at.run()
    assert not at.exception, [e.message for e in at.exception]


@pytest.mark.parametrize("role", ["sector_officer", "district_planner"])
def test_plan_page_by_role(built_db, role):
    user = next(u for u in DEMO_USERS if u.role == role)
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = user
    at.run()
    at.switch_page("views/plan.py")
    at.run()
    assert not at.exception, [e.message for e in at.exception]


def test_plan_page_with_decisions(built_db):
    """Regression: audit entries without a reason (NaN in pandas) must not break the timeline."""
    from irerero.db.session import engine
    from irerero.roles import User
    from irerero.track import plans

    planner = next(u for u in DEMO_USERS if u.role == "district_planner")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = planner
    at.run()  # first start builds the tables
    eng = engine()
    user = User(planner.user_id, planner.role, planner.name, district_id=planner.district_id)
    items = [
        {"geo_id": "S-MUHANGA-RONGI", "rank": 1, "places": 300, "rooms": 10, "caregivers_low": 10,
         "caregivers_high": 20, "bottleneck": "SUPPLY", "intervention": "Build rooms"},
        {"geo_id": "S-MUHANGA-CYEZA", "rank": 2, "places": 120, "rooms": 4, "caregivers_low": 4,
         "caregivers_high": 8, "bottleneck": "DEMAND", "intervention": "Outreach"},
    ]  # fmt: skip
    plan_id = plans.create_plan(eng, user, "D-MUHANGA", "Test plan", 0.65, "Balanced", {}, items)
    first, second = plans.items(eng, plan_id).id.tolist()
    plans.decide(eng, user, first, "approve")
    plans.decide(eng, user, second, "reject", "Centre opening nearby")
    plans.set_status(eng, user, first, "funded")
    at.switch_page("views/plan.py")
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    page = " ".join(m.value for m in at.markdown)
    assert "Rejected: Cyeza" in page and "Approved: Rongi" in page
