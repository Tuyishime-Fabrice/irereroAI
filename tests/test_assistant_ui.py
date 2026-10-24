"""The assistant in the running app (Streamlit AppTest): the Overview hero keeps both notices,
an unconfigured deployment says so instead of answering, a question goes through the real SDK
to the local Messages API stand-in and the answer lands in the conversation, and every other
screen offers the compact entry button."""

import pytest
from streamlit.testing.v1 import AppTest

from irerero.config import DEFINITION, ROOT
from irerero.roles import DEMO_USERS
from tests import fake_anthropic

APP = str(ROOT / "app" / "streamlit_app.py")
PLANNER = DEMO_USERS[0]


@pytest.fixture(scope="module")
def env():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope="module")
def built_db(tmp_path_factory, env):
    env.setenv("DATABASE_URL", f"sqlite:///{tmp_path_factory.mktemp('uidb') / 'app.sqlite'}")


@pytest.fixture(scope="module")
def api(env):
    server = fake_anthropic.serve()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def _app(user=PLANNER) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = user
    return at


def _html(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_overview_hero_keeps_both_notices_and_the_target(built_db, env):
    env.delenv("ANTHROPIC_API_KEY", raising=False)
    at = _app()
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    page = _html(at)
    assert DEFINITION in page and "never added together" in page
    assert "SIMULATED" in page and "left out of exports by default" in page  # demo data
    assert "NST2 target" in page and "65% by 2028/29" in page
    assert 'class="ir-title ir-sr"' in page  # the page still has its h1 for screen readers


def test_without_a_key_the_assistant_says_it_is_not_set_up(built_db, env):
    env.delenv("ANTHROPIC_API_KEY", raising=False)
    at = _app()
    at.run()
    box = at.chat_input[0]
    assert box.disabled
    assert "not set up" in box.placeholder
    assert "ANTHROPIC_API_KEY" in _html(at)


def test_a_question_is_answered_from_the_dashboard(built_db, env, api):
    env.setenv("ANTHROPIC_API_KEY", "test-key")
    env.setenv("IRERERO_ASSISTANT_BASE_URL", api)
    fake_anthropic.STATE.violations.clear()
    at = _app()
    at.run()
    assert not at.chat_input[0].disabled
    at.chat_input[0].set_value("What is the current pre-primary attendance rate?").run()
    assert not at.exception, [e.message for e in at.exception]
    texts = [" ".join(m.value for m in msg.markdown) for msg in at.chat_message]
    assert any("What is the current pre-primary attendance rate?" in t for t in texts)
    assert any("% of children aged 3-5 attend" in t and "simulated" in t for t in texts)
    # a follow-up keeps the conversation (append-only, checked by the stand-in)
    at.chat_input[0].set_value("And Muhanga?").run()
    texts = [" ".join(m.value for m in msg.markdown) for msg in at.chat_message]
    assert any("Muhanga needs" in t for t in texts)
    assert not fake_anthropic.STATE.violations
    # an empty question is not sent
    n = len(at.chat_message)
    at.chat_input[0].set_value("   ").run()
    assert len(at.chat_message) == n


@pytest.mark.parametrize(
    "page",
    ["views/priorities.py", "views/sector.py", "views/plan.py", "views/brief.py",
     "views/methods.py"],
)  # fmt: skip
def test_other_screens_offer_the_compact_entry(built_db, env, page):
    env.delenv("ANTHROPIC_API_KEY", raising=False)
    at = _app()
    at.run()
    at.switch_page(page)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert any(b.label.startswith("Ask IrereroAI") for b in at.button)
    assert not at.chat_input  # no banner on these screens: the question box is in the dialog


def test_switching_role_starts_a_new_conversation(built_db, env, api):
    env.setenv("ANTHROPIC_API_KEY", "test-key")
    env.setenv("IRERERO_ASSISTANT_BASE_URL", api)
    at = _app()
    at.run()
    at.chat_input[0].set_value("Which districts should we prioritize?").run()
    assert len(at.chat_message) >= 2
    at.sidebar.radio[0].set_value("National analyst").run()  # as a person would
    assert len(at.chat_message) == 0
