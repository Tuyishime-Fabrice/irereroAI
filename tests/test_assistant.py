"""The assistant: its figures come from the screens' own calculations, it respects roles,
and its conversation loop works end to end through the real SDK, against a local stand-in for
the Messages API (tests/fake_anthropic.py) that also checks the history is append-only."""

import socket

import pytest

from irerero.assistant import chat, facts
from irerero.diagnose import live
from irerero.plan import gap
from irerero.plan.frame import ranked
from irerero.plan.frame import sectors as plan_sectors
from irerero.roles import DEMO_USERS
from irerero.track import forecast
from tests import fake_anthropic

PLANNER, ANALYST, OFFICER, CAREGIVER, ADMIN = DEMO_USERS
TARGET = 0.65


@pytest.fixture(scope="module")
def t(tables, build_eng) -> facts.Tables:
    diag = live.frame(
        tables["observation"],
        tables["geo_unit"],
        tables["estimate_2026"],
        tables["model_output"],
        tables["model_run"],
        TARGET,
        None,
    ).merge(tables["geo_unit"][["geo_id", "name", "district"]], on="geo_id", how="left")
    return facts.Tables(
        sectors=plan_sectors(build_eng),
        forecast=tables["forecast"],
        diagnosis=diag,
        sources=tables["source"],
        model_run=tables["model_run"],
    )


@pytest.fixture(scope="module")
def server():
    srv = fake_anthropic.serve()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture
def config(server) -> chat.Config:
    fake_anthropic.STATE.violations.clear()
    return chat.Config(api_key="test-key", base_url=server)  # pragma: allowlist secret


def ask(config, t, question, history=(), user=PLANNER, page="Overview"):
    ctx = chat.Context(page=page, user=user, target=TARGET)
    events = list(
        chat.stream_turn(chat.make_client(config), config, list(history), question, ctx, t)
    )
    kinds = [k for k, _ in events]
    assert kinds[-1] == "done"
    return events[-1][1], "".join(v for k, v in events if k == "text"), kinds


# --- figures ------------------------------------------------------------------------------
def test_overview_figures_are_the_screens_figures(t):
    out = facts.overview(t, TARGET)
    needs = gap.needs(t.sectors, TARGET)
    e = out["estimate_2026"]
    assert e["places_needed_for_65pct"] == needs.places.sum()
    assert e["children_3_5"] == round(needs.children_3_5.sum())
    assert e["status"] == "simulated"  # the demo bundle is simulated, and says so
    nat = forecast.summary(t.forecast, TARGET).loc[forecast.NATIONAL]
    assert out["national_trend"]["projected_2028/29_pct"] == round(nat.projected * 100, 1)
    first = out["districts_needing_most_places"][0]
    by = needs.groupby("district").places.sum()
    assert first["district"] == by.idxmax() and first["places_needed"] == by.max()


def test_district_ranking_is_the_priority_screens_ranking(t):
    out = facts.district(t, "D-MUHANGA", TARGET, "Equity first")
    frame = t.sectors[t.sectors.district_id == "D-MUHANGA"]
    from irerero.config import COMPONENTS, PRESETS

    result, _ = ranked(frame, TARGET, dict(zip(COMPONENTS, PRESETS["Equity first"], strict=True)))
    assert [s["sector"] for s in out["priority"]["sectors"]] == result.name.tolist()
    assert out["estimate_2026"]["places_needed"] == result.places.sum()


def test_unknown_names_suggest_the_closest(t):
    with pytest.raises(facts.NotFound, match="Muhanga"):
        facts.find_district(t, "Muhangha")
    assert facts.find_district(t, "  muhanga district ") == "D-MUHANGA"
    with pytest.raises(facts.NotFound, match="Cyeza"):
        facts.find_sector(t, "Cyeza sektor", "D-MUHANGA")


def test_tools_respect_the_roles_screens(t):
    def run(name, user, **args):
        return chat.run_tool(name, args, chat.Context("x", user, TARGET), t)

    assert run("get_district", ANALYST, district="Gasabo")["priority"]["sectors"]
    other = run("get_district", PLANNER, district="Gasabo")
    assert "priority" not in other  # district figures yes, another district's sectors no
    with pytest.raises(PermissionError):
        run("get_sector", PLANNER, district="Gasabo", sector="Remera")
    assert run("get_sector", PLANNER, district="Muhanga", sector="Cyeza")["sector"] == "Cyeza"
    with pytest.raises(PermissionError):
        run("get_overview", OFFICER)
    with pytest.raises(PermissionError):
        run("get_sector", OFFICER, district="Muhanga", sector="Rongi")
    with pytest.raises(PermissionError):
        run("get_district", CAREGIVER, district="Muhanga")
    assert "real_files" in run("get_data_status", ADMIN)
    with pytest.raises(ValueError, match="target"):
        run("get_overview", ANALYST, target=65)


def test_config_reads_secrets_before_the_environment(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not chat.Config.from_env({}).ready
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    secrets = {"ANTHROPIC_API_KEY": "from-secrets"}  # pragma: allowlist secret
    cfg = chat.Config.from_env({**secrets, "IRERERO_ASSISTANT_FALLBACKS": "off"})
    assert cfg.api_key == secrets["ANTHROPIC_API_KEY"]
    assert cfg.model == chat.DEFAULT_MODEL and not cfg.fallbacks


# --- conversation, end to end through the SDK ----------------------------------------------
def test_answer_uses_a_tool_and_quotes_the_dashboard(config, t):
    turn, text, kinds = ask(config, t, "What is the current pre-primary attendance rate?")
    pct = facts.overview(t, TARGET)["estimate_2026"]["attending_pre_primary_pct"]
    assert f"{pct}%" in text and "simulated" in text
    assert "status" in kinds and turn.tools_used == ["get_overview"]
    # user question, assistant tool call, tool result, final answer
    assert [m["role"] for m in turn.messages] == ["user", "assistant", "user", "assistant"]
    thinking = [b for b in turn.messages[1]["content"] if b["type"] == "thinking"]
    assert thinking and thinking[0]["signature"].startswith("sig-")
    assert "<dashboard_context>" in turn.messages[0]["content"][0]["text"]
    assert not fake_anthropic.STATE.violations


def test_follow_up_questions_keep_the_history_append_only(config, t):
    first, _, _ = ask(config, t, "Which districts should we prioritize?")
    history = first.messages
    second, text, _ = ask(config, t, "And Muhanga?", history)
    assert "Muhanga needs" in text
    third, _, _ = ask(config, t, "What does the scope warning mean?", history + second.messages)
    assert third.tools_used == []
    assert not fake_anthropic.STATE.violations, fake_anthropic.STATE.violations


def test_a_refused_tool_call_is_explained_not_guessed(config, t):
    _, text, _ = ask(config, t, "Explain the sector Cyeza", user=ADMIN)
    assert "not available" in text and "role" in text


def test_refusal_and_truncation_are_reported(config, t):
    turn, _, _ = ask(config, t, "[refuse] something")
    assert turn.stop_reason == "refusal" and turn.messages == [] and turn.notice
    turn, _, _ = ask(config, t, "[long] tell me everything")
    assert turn.stop_reason == "max_tokens" and "cut short" in turn.notice


@pytest.mark.parametrize(
    ("marker", "words", "retryable"),
    [("[500]", "temporarily unavailable", True), ("[429]", "20 seconds", True),
     ("[401]", "API key", False)],
)  # fmt: skip
def test_api_failures_become_messages_a_person_can_act_on(config, t, marker, words, retryable):
    with pytest.raises(chat.AssistantError) as caught:
        ask(config, t, f"{marker} attendance?")
    assert words in caught.value.message and caught.value.retryable is retryable


def test_network_failure_and_a_wrong_key(t, server):
    with socket.socket() as s:  # a port nothing listens on
        s.bind(("127.0.0.1", 0))
        closed = s.getsockname()[1]
    down = chat.Config(api_key="test-key", base_url=f"http://127.0.0.1:{closed}")
    with pytest.raises(chat.AssistantError, match="Could not reach"):
        ask(down, t, "attendance?")
    wrong = chat.Config(api_key="not-the-key", base_url=server)
    with pytest.raises(chat.AssistantError, match="rejected the configured API key"):
        ask(wrong, t, "attendance?")


def test_requests_carry_the_frozen_prompt_tools_and_fallback(config, t):
    ask(config, t, "attendance?")
    body = fake_anthropic.STATE.requests[-1]
    assert body["system"][0]["text"] == chat.SYSTEM
    assert [x["name"] for x in body["tools"]] == [x["name"] for x in chat.TOOLS]
    assert body["model"] == "claude-opus-5-5" and body["fallbacks"] == "default"
    assert body["thinking"] == {"type": "adaptive"} and body["output_config"]["effort"]


def test_the_stand_in_catches_an_edited_history(config, t):
    """The append-only check is not vacuous: editing an earlier turn is reported."""
    first, _, _ = ask(config, t, "Which districts should we prioritize?")
    edited = [dict(m) for m in first.messages]
    edited[0] = {"role": "user", "content": [{"type": "text", "text": "a different question"}]}
    ask(config, t, "And Muhanga?", edited)
    assert "earlier messages were edited, not appended" in fake_anthropic.STATE.violations
