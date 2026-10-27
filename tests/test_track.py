"""TRACK: trend, back-test, status, what-if, and plan decisions with their audit entries."""

from datetime import date

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from irerero import audit
from irerero.config import PROJECTION_YEARS, TARGET_YEAR, YEARBOOK_YEARS
from irerero.db.models import AuditLog, Base
from irerero.roles import ADMIN, ANALYST, PLANNER, User
from irerero.track import forecast, plans

PLANNER_USER = User("p1", PLANNER, "Planner", district_id="D-A")
OTHER_PLANNER = User("p2", PLANNER, "Planner B", district_id="D-B")
ADMIN_USER = User("a1", ADMIN, "Admin")
ANALYST_USER = User("n1", ANALYST, "Analyst")


def test_trend_prediction_interval():
    x = np.array([2020, 2021, 2022, 2023, 2024], float)
    exact = forecast.fit(x, 0.2 + 0.05 * (x - 2020))
    c, lo, hi = exact.predict(2028)
    assert c == pytest.approx(0.60)
    assert hi - lo == pytest.approx(0, abs=1e-9)
    noisy = forecast.fit(x, 0.2 + 0.05 * (x - 2020) + np.array([0.01, -0.01, 0.02, -0.02, 0]))
    c, lo, hi = noisy.predict(2028)
    assert lo < c < hi
    _, lo2, hi2 = noisy.predict(2026)
    assert hi2 - lo2 < hi - lo  # wider further out


@pytest.mark.parametrize(
    ("central", "high", "status"),
    [(0.66, 0.70, "on track"), (0.60, 0.66, "at risk"), (0.50, 0.60, "off track")],
)
def test_status(central, high, status):
    assert forecast.status_for(central, high, 0.65) == status


def test_places_per_year():
    assert forecast.places_per_year(3000, 10_000, 0.65, 4) == pytest.approx(875)
    assert forecast.places_per_year(9000, 10_000, 0.65, 4) == 0


def test_whatif_adds_rooms_from_first_year():
    years = list(PROJECTION_YEARS)
    projected = pd.Series([0.40, 0.42, 0.44, 0.46], index=years)
    children = pd.Series([10_000.0] * 4, index=years)
    out = forecast.whatif(projected, children, rooms_per_year=10, first_year="2026/27")
    # 10 rooms x 30 places = 300 a year: +0, +3, +6, +9 points
    assert out.tolist() == pytest.approx([0.40, 0.45, 0.50, 0.55])


def test_built_forecast(tables):
    f = tables["forecast"]
    assert set(f.kind) == {"observed", "projected", "backtest"}
    districts = set(f.geo_id) - {forecast.NATIONAL}
    assert len(districts) == 30
    assert len(f[f.kind == "observed"]) == 31 * len(YEARBOOK_YEARS)
    summary = forecast.summary(f)
    assert set(summary.status) <= {"on track", "at risk", "off track"}
    proj = f[(f.kind == "projected") & (f.year == TARGET_YEAR)]
    assert (proj.low <= proj.value).all()
    assert (proj.value <= proj.high).all()


@pytest.fixture
def plan_eng(tmp_path):
    e = create_engine(f"sqlite:///{tmp_path / 'plans.sqlite'}")
    Base.metadata.create_all(e)
    return e


ITEMS = [
    {"geo_id": "S-A-1", "rank": 1, "places": 350, "rooms": 12, "caregivers_low": 12,
     "caregivers_high": 24, "bottleneck": "SUPPLY", "intervention": "Build rooms"},
    {"geo_id": "S-A-2", "rank": 2, "places": 100, "rooms": 4, "caregivers_low": 4,
     "caregivers_high": 7, "bottleneck": "DEMAND", "intervention": "Parent outreach"},
]  # fmt: skip


def make_plan(plan_eng) -> tuple[int, pd.DataFrame]:
    plan_id = plans.create_plan(
        plan_eng, PLANNER_USER, "D-A", "Plan", 0.65, "Balanced", {"volume": 0.3}, ITEMS
    )
    return plan_id, plans.items(plan_eng, plan_id)


def last_entry(plan_eng) -> AuditLog:
    with Session(plan_eng) as s:
        return s.query(AuditLog).order_by(AuditLog.id.desc()).first()


def test_create_plan_is_audited(plan_eng):
    plan_id, items = make_plan(plan_eng)
    assert items.decision.tolist() == ["pending", "pending"]
    entry = last_entry(plan_eng)
    assert (entry.action, entry.user_id, entry.entity_id) == ("plan.create", "p1", str(plan_id))
    assert entry.at is not None


def test_approve_edit_reject_each_write_an_audit_entry(plan_eng):
    _, items = make_plan(plan_eng)
    first, second = items.id.tolist()

    plans.decide(plan_eng, PLANNER_USER, first, "approve")
    entry = last_entry(plan_eng)
    assert entry.action == "plan_item.approve"
    assert entry.user_id == "p1" and entry.at is not None

    plans.decide(
        plan_eng, PLANNER_USER, first, "edit", "Land available for only 6 rooms", places=180
    )
    entry = last_entry(plan_eng)
    assert entry.action == "plan_item.edit"
    assert entry.reason == "Land available for only 6 rooms"
    assert entry.before["places"] == 350
    assert entry.after == {**entry.after, "places": 180, "rooms": 6, "caregivers_low": 6,
                           "caregivers_high": 12, "decision": "edited"}  # fmt: skip

    plans.decide(plan_eng, PLANNER_USER, second, "reject", "NGO centre opening in 2027")
    entry = last_entry(plan_eng)
    assert entry.action == "plan_item.reject"
    assert entry.reason == "NGO centre opening in 2027"
    assert plans.items(plan_eng, 1).decision.tolist() == [
        "edited",
        "rejected",
    ]


@pytest.mark.parametrize("decision", ["edit", "reject"])
def test_edit_and_reject_need_a_reason(plan_eng, decision):
    _, items = make_plan(plan_eng)
    with pytest.raises(ValueError, match="reason"):
        plans.decide(plan_eng, PLANNER_USER, int(items.id.iat[0]), decision, "  ", places=10)


@pytest.mark.parametrize("user", [OTHER_PLANNER, ADMIN_USER, ANALYST_USER], ids=lambda u: u.user_id)
def test_only_the_district_planner_decides(plan_eng, user):
    _, items = make_plan(plan_eng)
    with pytest.raises(plans.NotAllowed):
        plans.decide(plan_eng, user, int(items.id.iat[0]), "approve")


def test_status_follows_approval(plan_eng):
    _, items = make_plan(plan_eng)
    item = int(items.id.iat[0])
    with pytest.raises(ValueError, match="approved"):
        plans.set_status(plan_eng, PLANNER_USER, item, "funded")
    plans.decide(plan_eng, PLANNER_USER, item, "approve")
    plans.set_status(plan_eng, PLANNER_USER, item, "funded")
    assert last_entry(plan_eng).action == "plan_item.status"
    assert plans.items(plan_eng, 1).status.iat[0] == "funded"


def test_audit_log_is_append_only(plan_eng):
    make_plan(plan_eng)
    with Session(plan_eng) as s:
        entry = s.query(AuditLog).first()
        entry.reason = "tampered"
        with pytest.raises(audit.AuditImmutable):
            s.commit()
    with Session(plan_eng) as s:
        s.delete(s.query(AuditLog).first())
        with pytest.raises(audit.AuditImmutable):
            s.commit()


def test_whatif_counts_places_only_up_to_the_need():
    years = list(PROJECTION_YEARS)
    projected = pd.Series([0.40, 0.42, 0.44, 0.46], index=years)
    children = pd.Series([10_000.0] * 4, index=years)
    out = forecast.whatif(projected, children, 10, "2026/27", max_places=500)
    # 300, 600, 900 places added, but only 500 are needed: +3, +5, +5 points
    assert out.tolist() == pytest.approx([0.40, 0.45, 0.49, 0.51])


def test_add_items_to_an_existing_plan(plan_eng):
    plan_id, _ = make_plan(plan_eng)
    new = {**ITEMS[0], "geo_id": "S-A-3", "rank": 3}
    added = plans.add_items(plan_eng, PLANNER_USER, plan_id, [ITEMS[0], new])
    items = plans.items(plan_eng, plan_id)
    assert items.geo_id.tolist() == ["S-A-1", "S-A-2", "S-A-3"]  # S-A-1 not added twice
    assert len(added) == 1
    assert items.set_index("geo_id").loc["S-A-3", "decision"] == "pending"
    entry = last_entry(plan_eng)
    assert (entry.action, entry.entity_id) == ("plan_item.add", str(added[0]))
    assert entry.after["geo_id"] == "S-A-3"


@pytest.mark.parametrize("user", [OTHER_PLANNER, ADMIN_USER, ANALYST_USER], ids=lambda u: u.user_id)
def test_only_the_district_planner_adds_items(plan_eng, user):
    plan_id, _ = make_plan(plan_eng)
    with pytest.raises(plans.NotAllowed):
        plans.add_items(plan_eng, user, plan_id, [{**ITEMS[0], "geo_id": "S-A-3"}])


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_changed_places_need_an_edit(plan_eng, decision):
    _, items = make_plan(plan_eng)
    item = int(items.id.iat[0])
    with pytest.raises(ValueError, match="choose edit"):
        plans.decide(plan_eng, PLANNER_USER, item, decision, "A reason", places=7)
    assert plans.items(plan_eng, 1).places.iat[0] == 350  # unchanged
    plans.decide(plan_eng, PLANNER_USER, item, "approve", places=350)  # same places: fine
    assert plans.items(plan_eng, 1).decision.iat[0] == "approved"


@pytest.mark.parametrize(
    ("today", "now", "left"),
    [
        (date(2026, 10, 27), "2026/27", ("2026/27", "2027/28", "2028/29")),
        (date(2026, 8, 31), "2025/26", ("2025/26", "2026/27", "2027/28", "2028/29")),
        (date(2029, 9, 1), "2029/30", ()),
    ],
)
def test_school_years_left_follow_the_date(today, now, left):
    assert forecast.school_year_now(today) == now
    assert forecast.years_left(today) == left


def test_rooms_fill_no_places_in_demand_sectors():
    places = pd.Series({"S1": 300, "S2": 200, "S3": 100})
    main = pd.Series({"S1": "SUPPLY", "S2": "DEMAND", "S3": "UNCLEAR"})
    assert forecast.fillable_places(places, main) == 400


def test_earlier_plan_versions_are_read_only(plan_eng):
    old_id, old_items = make_plan(plan_eng)
    new_id = plans.create_plan(
        plan_eng, PLANNER_USER, "D-A", "Plan v2", 0.65, "Balanced", {}, ITEMS, replaces=old_id
    )
    assert last_entry(plan_eng).after["replaces"] == old_id
    assert plans.plans(plan_eng, "D-A").plan_id.tolist() == [new_id, old_id]  # newest first
    old_item = int(old_items.id.iat[0])
    with pytest.raises(ValueError, match="read-only"):
        plans.decide(plan_eng, PLANNER_USER, old_item, "approve")
    with pytest.raises(ValueError, match="read-only"):
        plans.add_items(plan_eng, PLANNER_USER, old_id, [{**ITEMS[0], "geo_id": "S-A-9"}])
    new_item = int(plans.items(plan_eng, new_id).id.iat[0])
    plans.decide(plan_eng, PLANNER_USER, new_item, "approve")  # the current version changes
    assert plans.items(plan_eng, old_id).decision.tolist() == ["pending", "pending"]
