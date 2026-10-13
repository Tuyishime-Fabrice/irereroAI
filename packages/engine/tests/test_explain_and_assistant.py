import pytest

from irerero_engine.assistant import AssistantContext, TemplateAssistant, classify
from irerero_engine.explain import TemplateExplainer, alert_reason
from irerero_engine.features import FEATURES
from irerero_engine.types import Driver, SourceRef

EVIDENCE: dict[str, dict[str, float | int | str]] = {
    "attendance_drop": {
        "attendance": 14,
        "enrolled": 40,
        "rate": 0.35,
        "usual_rate": 0.84,
        "weeks": 3,
        "main_problem": "no_water",
    },
    "missing_report": {"weeks_missing": 3, "last_report": "2026-08-31"},
    "overcrowding": {"attendance": 81, "capacity": 60, "waiting_list": 53},
    "wash": {"weeks": 2},
    "closure_risk": {"days_open": 0, "main_problem": "building_damage"},
}


@pytest.mark.parametrize("kind", sorted(EVIDENCE))
def test_every_alert_kind_has_both_languages(kind: str) -> None:
    en, rw = alert_reason(kind, "Irerero Umucyo", EVIDENCE[kind])
    assert "Irerero Umucyo" in en and "Irerero Umucyo" in rw
    assert en != rw


def test_suggestion_explains_numbers_and_never_claims_stunting_reduction() -> None:
    feature = FEATURES["uncovered_children"]
    driver = Driver(feature.key, feature.label_en, feature.label_rw, 1.0)
    numbers = {
        "reached": 74,
        "reached_low": 60,
        "reached_high": 88,
        "high_risk": 35,
        "mothers": 9,
        "cost": 25_000_000,
    }
    en, rw = TemplateExplainer().suggestion("build", "Cyumba site A", numbers, [driver], 30)
    assert "between 60 and 88" in en and "25,000,000 RWF" in en
    assert "reduce" not in en.lower() and "reduction" not in en.lower()
    assert "hagati ya 60 na 88" in rw


def test_assistant_names_source_tables() -> None:
    context = AssistantContext(
        subject="Build",
        explanation_en="Because.",
        explanation_rw="Kubera.",
        range_en="Between 60 and 88.",
        range_rw="Hagati ya 60 na 88.",
        sources=[SourceRef("need_estimate", "IrereroAI demo generator", 2026, "simulated")],
    )
    answer = TemplateAssistant().answer("Which data does this use?", "en", context)
    assert answer.question == "sources"
    assert answer.tables == ("need_estimate",)
    assert "simulated" in answer.text
    assert classify("who decides?") == "who_decides"
    assert classify("weather tomorrow") is None
