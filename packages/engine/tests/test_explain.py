from irerero_engine.explain import TemplateExplainer
from irerero_engine.features import FEATURES
from irerero_engine.types import Driver


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
    flat = dict(numbers, reached_low=74, reached_high=74)
    assert "between" not in TemplateExplainer().suggestion("build", "A", flat, [driver], 30)[0]
    assert "reduce" not in en.lower() and "reduction" not in en.lower()
    assert "hagati ya 60 na 88" in rw
