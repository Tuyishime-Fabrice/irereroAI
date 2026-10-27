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
    assert 'class="ir-fresh-' in page  # the decision just recorded glows once


# --- journeys across screens: each one broke before it was tested here ----------------------


def _other_district():
    """A district other than Muhanga, so a journey's plan does not meet another test's."""
    from irerero.db.session import engine
    from irerero.db.store import read

    units = read(engine(), "geo_unit")
    districts = units[(units.level == "district") & (units.geo_id != "D-MUHANGA")]
    district_id = districts.sort_values("geo_id").geo_id.iat[0]
    sectors = units[units.parent_id == district_id].sort_values("geo_id").geo_id.tolist()
    return district_id, sectors


def test_sector_added_after_the_plan_exists_reaches_the_plan(built_db):
    """Sector diagnosis -> Add to action plan -> Action plans -> Add to this plan. Then a
    changed number of places with "approve" is refused, not dropped."""
    from irerero.db.session import engine
    from irerero.roles import PLANNER, User
    from irerero.track import plans

    at = AppTest.from_file(APP, default_timeout=180)
    at.run()  # builds the tables on first start
    district_id, sectors = _other_district()
    user = User("demo-planner", PLANNER, "Demo planner (fictional)", district_id=district_id)
    eng = engine()
    first = {"geo_id": sectors[0], "rank": 1, "places": 100, "rooms": 4, "caregivers_low": 4,
             "caregivers_high": 7, "bottleneck": "SUPPLY", "intervention": "Build"}  # fmt: skip
    plan_id = plans.create_plan(eng, user, district_id, "Journey", 0.65, "Balanced", {}, [first])

    at.session_state["user"] = user
    at.switch_page("views/sector.py")
    at.run()
    at.selectbox(key="sector-pick").set_value(sectors[1]).run()
    next(b for b in at.button if b.label == "Add to action plan").click().run()
    assert at.session_state["plan_basket"] == [sectors[1]]

    at.switch_page("views/plan.py")
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    next(b for b in at.button if b.label == "Add 1 to this plan").click().run()
    assert not at.exception, [e.message for e in at.exception]
    items = plans.items(eng, plan_id)
    assert set(items.geo_id) == {sectors[0], sectors[1]}
    assert at.session_state["plan_basket"] == []
    assert "Added to plan" in " ".join(m.value for m in at.markdown)  # in the timeline

    item = int(items.set_index("geo_id").at[sectors[0], "id"])
    at.radio(key=f"dec-{item}").set_value("approve")
    at.number_input(key=f"pl-{item}").set_value(7)
    at.button(key=f"FormSubmitter:decide-{item}-Record decision").click().run()
    assert any("choose edit" in e.value for e in at.error)
    assert plans.items(eng, plan_id).set_index("id").at[item, "decision"] == "pending"


def test_pdf_leaves_out_simulated_learn_figures(built_db, monkeypatch):
    """With simulated values excluded, the PDF must not carry the simulated LEARN line."""
    from irerero import brief

    sent = []
    real = brief.pdf

    def spy(title, lines, *args, **kwargs):
        sent.append(lines)
        return real(title, lines, *args, **kwargs)

    monkeypatch.setattr(brief, "pdf", spy)
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    at.switch_page("views/brief.py")
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert "LEARN pilot" in " ".join(m.value for m in at.markdown)  # shown on the page
    assert not any("LEARN pilot" in line for line in sent[-1])

    at.toggle[0].set_value(True).run()  # include simulated values, labelled
    assert any("LEARN pilot" in line for line in sent[-1])


def test_quiz_pass_keeps_the_course_open_with_its_certificate(built_db):
    from irerero.db.session import engine
    from irerero.db.store import read
    from irerero.learn import progress

    caregiver = next(u for u in DEMO_USERS if u.role == "caregiver")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = caregiver
    at.run()
    eng = engine()
    mine = progress.assignments(eng, [caregiver.user_id])
    open_ = mine[mine.completed_at.isna() & mine.status.isin(["required", "recommended"])]
    pick = int(open_.id.iat[0])
    at.selectbox(key="course-pick").set_value(pick).run()
    quiz = read(eng, "quiz_item")
    course_id = open_.set_index("id").at[pick, "course_id"]
    for q in quiz[quiz.course_id == course_id].itertuples():
        at.radio(key=f"q-{pick}-{q.position}").set_value(q.options[q.answer])
    at.button(key=f"FormSubmitter:quiz-{pick}-Submit answers").click().run()
    assert at.success and "course completed" in at.success[0].value
    assert len(at.get("download_button")) == 1  # the certificate, straight away

    at.run()  # the course is now Completed and moves in the list
    assert at.selectbox(key="course-pick").value == pick
    assert len(at.get("download_button")) == 1


def test_checkin_form_keeps_the_last_water_answer(built_db):
    """A correction must not flip 'no water' back to 'yes' by default."""
    from irerero.db.session import engine
    from irerero.learn import checkins

    caregiver = next(u for u in DEMO_USERS if u.role == "caregiver")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = caregiver
    at.run()
    checkins.submit(
        engine(),
        caregiver,
        checkins.Checkin(caregiver.centre_id, checkins.current_month(), 30, 20.0, 2, 4.0, False,
                         "no_water"),
    )  # fmt: skip
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = caregiver
    at.run()
    assert next(r for r in at.radio if r.label.startswith("Water")).value == "No · Oya"
    assert next(s for s in at.selectbox if s.label.startswith("Main challenge")).value == "no_water"


def test_target_other_than_nst2_is_named_as_such(built_db):
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    next(s for s in at.slider if s.label.startswith("Target")).set_value(80).run()
    assert "Planning at 80%" in " ".join(m.value for m in at.markdown)
    at.switch_page("views/plan.py")
    at.run()
    page = " ".join(m.value for m in at.markdown)
    assert "Your 2028/29 target (NST2: 65%)" in page


# --- low-priority fixes from the QA review ------------------------------------------------


def _at_target(district_id, target):
    """Sectors of a district already at `target`: no places needed."""
    from irerero.db.session import engine
    from irerero.plan import frame, gap

    rows = frame.sectors(engine())
    needs = gap.needs(rows[rows.district_id == district_id], target)
    return needs[needs.places == 0].geo_id.tolist(), needs[needs.places > 0].geo_id.tolist()


def test_add_to_plan_needs_a_choice_and_skips_sectors_at_target(built_db):
    planner = next(u for u in DEMO_USERS if u.role == "district_planner")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = planner
    at.session_state["target_pct"] = 30  # low enough that some sectors are already there
    at.run()
    at.switch_page("views/priorities.py")
    at.run()
    assert next(b for b in at.button if b.label == "Add to plan").disabled  # nothing chosen
    done, short = _at_target(planner.district_id, 0.30)
    assert done and short, "the test needs one sector at the target and one below it"
    next(m for m in at.multiselect if m.label.startswith("Add sectors")).set_value(
        [done[0], short[0]]
    ).run()
    next(b for b in at.button if b.label == "Add to plan").click().run()
    assert at.session_state["plan_basket"] == [short[0]]
    assert any("Already at the target" in w.value for w in at.warning)

    at.switch_page("views/sector.py")
    at.run()
    at.selectbox(key="sector-pick").set_value(done[0]).run()
    assert next(b for b in at.button if b.label == "Add to action plan").disabled


def test_checkin_shows_submitted_straight_after_saving(built_db):
    caregiver = next(u for u in DEMO_USERS if u.role == "caregiver")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = caregiver
    at.run()
    present = next(n for n in at.number_input if n.label.startswith("Children present"))
    assert present.proto.format == "%g"  # 31, not 31.00
    next(n for n in at.number_input if n.label.startswith("Children enrolled")).set_value(30)
    present.set_value(20.0)
    at.button(key="FormSubmitter:checkin-Submit · Ohereza").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert any("Check-in saved" in s.value for s in at.success)
    page = " ".join(m.value for m in at.markdown)
    assert '<div class="value">Submitted</div>' in page


def test_quiz_with_blank_answers_is_not_scored(built_db):
    from irerero.db.session import engine
    from irerero.learn import progress

    caregiver = next(u for u in DEMO_USERS if u.role == "caregiver")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = caregiver
    at.run()
    pick = at.selectbox(key="course-pick").value
    before = progress.assignments(engine(), [caregiver.user_id]).set_index("id").at[pick, "score"]
    at.button(key=f"FormSubmitter:quiz-{pick}-Submit answers").click().run()
    assert any("Answer all" in w.value for w in at.warning)
    after = progress.assignments(engine(), [caregiver.user_id]).set_index("id").at[pick, "score"]
    assert after == before or (after != after and before != before)  # unchanged, NaN included


def test_admin_area_comes_from_real_units(built_db):
    from irerero.db.session import engine
    from irerero.db.store import read

    admin = next(u for u in DEMO_USERS if u.role == "admin")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = admin
    at.run()
    units = read(engine(), "geo_unit")
    district = "D-MUHANGA"
    inside = units[(units.level == "sector") & (units.parent_id == district)].geo_id.iat[0]
    outside = units[(units.level == "sector") & (units.parent_id != district)].geo_id.iat[0]

    def save(district_choice, sector_choice):
        next(s for s in at.selectbox if s.label == "User").set_value("demo-analyst")
        next(s for s in at.selectbox if s.label == "Role").set_value("national_analyst")
        next(s for s in at.selectbox if s.label == "District").set_value(district_choice)
        next(s for s in at.selectbox if s.label == "Sector").set_value(sector_choice)
        at.button(key="FormSubmitter:role-Save").click().run()
        return read(engine(), "app_user").set_index("user_id").loc["demo-analyst"]

    row = save(district, outside)  # a sector outside the district is refused
    assert any("is not in" in e.value for e in at.error)
    assert row.sector_id is None or row.sector_id != outside
    row = save(district, inside)
    assert (row.district_id, row.sector_id) == (district, inside)
    row = save("(keep current)", "(none)")  # a field can be cleared
    assert row.district_id == district and not isinstance(row.sector_id, str)


# --- account menu: language and appearance ------------------------------------------------


def test_account_menu_switches_language_and_appearance(built_db):
    from html import escape

    planner = next(u for u in DEMO_USERS if u.role == "district_planner")
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = planner
    at.run()
    at.switch_page("views/priorities.py")
    at.run()
    page = lambda: " ".join(m.value for m in at.markdown)  # noqa: E731
    assert "Sector ranking and needs" in page() and "filter: invert(1)" not in page()
    at.selectbox(key="preset-en").set_value("Equity first").run()

    at.button(key="pref-lang").click().run()  # Ikinyarwanda
    assert not at.exception, [e.message for e in at.exception]
    assert escape("Urutonde rw'imirenge n'ibikenewe") in page()  # titles are HTML-escaped
    assert "Uburinganire mbere" in at.selectbox(key="preset-rw").options  # shown in Kinyarwanda
    assert at.session_state["preset"] == "Equity first"  # kept, where the assistant reads it

    at.button(key="pref-theme").click().run()  # dark
    assert "filter: invert(1)" in page()

    at.button(key="pref-lang").click().run()  # back to English
    at.button(key="pref-theme").click().run()  # back to light
    assert not at.exception, [e.message for e in at.exception]
    assert "Sector ranking and needs" in page() and "filter: invert(1)" not in page()
