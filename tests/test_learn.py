"""LEARN: course content, simulated pilot with planted problems, triggers, officer confirmation
with an audit entry, caregiver progress and aggregates."""

from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from irerero.db.models import AuditLog, Base
from irerero.db.store import replace_analysis
from irerero.learn import checkins, content, progress, simulate, triggers
from irerero.learn.checkins import Checkin
from irerero.roles import CAREGIVER, OFFICER, User

OFFICER_USER = User("demo-officer", OFFICER, "Officer", "D-MUHANGA", "S-MUHANGA-CYEZA")
OTHER_OFFICER = User("o2", OFFICER, "Officer B", "D-MUHANGA", "S-MUHANGA-RONGI")
DEMO_CARER = User("demo-caregiver", CAREGIVER, "Carer", "D-MUHANGA", "S-MUHANGA-CYEZA",
                  "SIM-MUH-001")  # fmt: skip


def test_course_content_rules():
    tables = content.load()
    assert len(tables["course"]) == 4
    assert tables["course"].required_on_joining.sum() == 2
    counts = tables["lesson"].groupby("course_id").size()
    assert counts.between(3, 5).all()
    assert (tables["quiz_item"].groupby("course_id").size() == 5).all()
    assert tables["course"].source.str.len().gt(10).all()  # every course cites its source
    assert tables["lesson"].body_md.str.contains("Source:").all()
    assert tables["course"].title_rw.str.len().gt(0).all()


@pytest.fixture
def eng(tmp_path, tables):
    e = create_engine(f"sqlite:///{tmp_path / 'learn.sqlite'}")
    Base.metadata.create_all(e)
    replace_analysis(e, {k: tables[k] for k in ("geo_unit", "source", "supply_extract", "course",
                                                "lesson", "quiz_item")})  # fmt: skip
    assert simulate.seed(e)
    return e


@pytest.fixture
def diag(tables):
    from irerero.diagnose import live

    return live.frame(tables["observation"], tables["geo_unit"], tables["estimate_2026"],
                      tables["model_output"], tables["model_run"], 0.65)  # fmt: skip


def test_simulation_plants_the_problems(eng):
    latest = checkins.problems(checkins.frame(eng)).set_index("centre_id")
    assert latest.at[simulate.NO_WATER, "no_water"]
    assert latest.at[simulate.FEW_MEALS, "few_meals"]
    assert latest.at[simulate.DROP, "attendance_drop"]
    assert (checkins.frame(eng).status == "simulated").all()
    assert not simulate.seed(eng)  # runs once


def test_triggers_fire_on_planted_problems(eng):
    added = triggers.run(eng)
    assert ("demo-caregiver", "wash", "checkin:no_water") in added
    assert ("sim-cg-002", "nutrition", "checkin:few_meals") in added
    flagged = progress.assignments(eng)
    new = flagged[flagged.trigger.str.startswith("checkin")]
    assert set(new.status) == {"recommended"}  # nothing becomes required automatically
    assert new.required_by.isna().all()
    assert triggers.run(eng) == []  # no duplicates


def test_sector_triggers(eng, diag):
    flags = triggers.sector_flags(diag)
    added = triggers.run(eng, diag)
    for carer, course, trigger in added:
        if trigger.startswith("sector:"):
            assert (
                trigger.split(":")[1]
                in flags[progress.caregivers(eng).set_index("caregiver_id").at[carer, "sector_id"]]
            )
            assert course in ("wash", "nutrition")


def test_officer_confirmation_is_audited(eng):
    triggers.run(eng)
    a = progress.assignments(eng, ["demo-caregiver"])
    wash = int(a[a.course_id == "wash"].id.iat[0])
    with pytest.raises(PermissionError):
        progress.confirm(eng, OTHER_OFFICER, wash, date(2026, 12, 1))
    progress.confirm(eng, OFFICER_USER, wash, date(2026, 12, 1), "Water point broken")
    with Session(eng) as s:
        entry = s.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert entry.action == "assignment.confirm"
    assert entry.user_id == "demo-officer" and entry.at is not None
    assert entry.reason == "Water point broken"
    row = progress.assignments(eng, ["demo-caregiver"]).set_index("course_id").loc["wash"]
    assert (row.status, row.required_by, row.due_date) == ("required", "officer", date(2026, 12, 1))


def test_dismiss_needs_a_reason(eng):
    triggers.run(eng)
    a = progress.assignments(eng, ["sim-cg-002"])
    item = int(a[a.course_id == "nutrition"].id.iat[0])
    with pytest.raises(ValueError, match="reason"):
        progress.dismiss(eng, OFFICER_USER, item, " ")


def test_caregiver_progress_quiz_and_privacy(eng):
    a = progress.assignments(eng, ["demo-caregiver"]).set_index("course_id")
    safeguarding = int(a.at["safeguarding", "id"])
    other = progress.assignments(eng, ["sim-cg-002"]).id.iat[0]
    with pytest.raises(PermissionError):
        progress.mark_lesson(eng, DEMO_CARER, int(other), 1)
    progress.mark_lesson(eng, DEMO_CARER, safeguarding, 2)
    wrong = progress.submit_quiz(eng, DEMO_CARER, safeguarding, {1: 0, 2: 0, 3: 0, 4: 1, 5: 0})
    assert not wrong["passed"]
    right = progress.submit_quiz(eng, DEMO_CARER, safeguarding, {1: 1, 2: 1, 3: 1, 4: 0, 5: 1})
    assert right == {"correct": 5, "total": 5, "score": 1.0, "passed": True}
    row = progress.assignments(eng, ["demo-caregiver"]).set_index("course_id").loc["safeguarding"]
    assert row.status == "completed" and row.completed_at is not None


def test_checkin_validation_and_ownership(eng):
    good = Checkin("SIM-MUH-001", "2026-10", 40, 33, 2, 4.5, True, "none")
    checkins.submit(eng, DEMO_CARER, good)
    with pytest.raises(PermissionError):
        checkins.submit(
            eng, DEMO_CARER, Checkin("SIM-MUH-002", "2026-10", 40, 33, 2, 4, True, "none")
        )
    with pytest.raises(ValueError, match="more than children enrolled"):
        checkins.submit(
            eng, DEMO_CARER, Checkin("SIM-MUH-001", "2026-10", 10, 33, 2, 4, True, "none")
        )
    with pytest.raises(ValueError, match="between 0 and 6"):
        checkins.submit(
            eng, DEMO_CARER, Checkin("SIM-MUH-001", "2026-10", 40, 3, 2, 7, True, "none")
        )
    latest = checkins.problems(checkins.frame(eng, ["SIM-MUH-001"])).iloc[0]
    assert latest.month == "2026-10" and not latest.no_water


def test_aggregates_hide_small_groups(eng):
    s = progress.summary(eng, today=date(2026, 10, 17))
    by_centre = progress.aggregate(s, "centre_id")
    assert by_centre.average_score.isna().all()  # one caregiver per centre: never shown
    by_district = progress.aggregate(s, "district_id")
    assert by_district.average_score.notna().all()
    assert s.overdue.any()  # planted: simulated joining courses past their due date
    completion = progress.completion_by_district(eng)
    assert set(completion) == {"D-MUHANGA"}
    assert 0 < completion["D-MUHANGA"] < 1


def test_training_completion_feeds_capacity(tables, eng):
    from irerero.diagnose import rules
    from irerero.diagnose.features import sector_features

    features = sector_features(tables["observation"], tables["geo_unit"], tables["estimate_2026"])
    base = rules.factors(features)
    with_learn = rules.factors(features, progress.completion_by_district(eng))
    muhanga = features.district_id == "D-MUHANGA"
    assert not with_learn.loc[muhanga, "capacity"].equals(base.loc[muhanga, "capacity"])
    pd.testing.assert_series_equal(
        with_learn.loc[~muhanga, "capacity"], base.loc[~muhanga, "capacity"]
    )
