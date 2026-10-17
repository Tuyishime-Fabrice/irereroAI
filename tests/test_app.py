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
    "page", ["views/national.py", "views/priorities.py", "views/sector.py", "views/methods.py"]
)
def test_planner_pages_render(built_db, page):
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    at.switch_page(page)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.title
