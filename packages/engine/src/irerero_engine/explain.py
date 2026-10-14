"""Explainer: plain-language explanations in English and Kinyarwanda from drivers and numbers.

Phase 1 baseline: rule-based reasons and templates. Phase 2: SHAP drivers from a fitted need
model feed the same templates.

Kinyarwanda templates are drafts until reviewed; all are listed in docs/i18n-review.md.
"""

from collections.abc import Mapping, Sequence
from typing import Protocol

from irerero_engine.types import Driver

ACTIONS = {
    "build": ("Build a new centre", "Kubaka irerero rishya"),
    "upgrade": ("Upgrade the home-based centre", "Kuzamura urugo mbonezamikurire"),
    "support": ("Support quality", "Gushyigikira ireme"),
}


def number(value: float) -> str:
    return f"{round(value):,}"


def percent(share: float | int | str) -> str:
    return f"{round(float(share) * 100)}%"


def _drivers_text(drivers: Sequence[Driver], language: str) -> str:
    labels = [d.label_en if language == "en" else d.label_rw for d in drivers]
    return "; ".join(label[0].lower() + label[1:] for label in labels)


class Explainer(Protocol):
    version: str

    def suggestion(
        self,
        action: str,
        site_name: str,
        numbers: Mapping[str, float],
        drivers: Sequence[Driver],
        catchment_minutes: int,
    ) -> tuple[str, str]: ...


class TemplateExplainer:
    version = "explainer-templates-1"

    def suggestion(
        self,
        action: str,
        site_name: str,
        numbers: Mapping[str, float],
        drivers: Sequence[Driver],
        catchment_minutes: int,
    ) -> tuple[str, str]:
        """`numbers` holds reached, reached_low, reached_high, high_risk, mothers, cost,
        and supported for support actions."""
        n = numbers
        action_en, action_rw = ACTIONS[action]
        reasons_en, reasons_rw = _drivers_text(drivers, "en"), _drivers_text(drivers, "rw")
        cost = number(n["cost"])
        if action == "support":
            en = (
                f"{action_en} at {site_name}, where {number(n['supported'])} children are "
                f"enrolled. Main reasons: {reasons_en}. Estimated cost: {cost} RWF."
            )
            rw = (
                f"{action_rw} kuri {site_name}, ahari abana {number(n['supported'])} banditswe. "
                f"Impamvu nyamukuru: {reasons_rw}. Igiciro giteganyijwe: {cost} RWF."
            )
            return en, rw
        reached = number(n["reached"])
        spread = number(n["reached_low"]) != number(n["reached_high"])
        range_en = f" (between {number(n['reached_low'])} and {number(n['reached_high'])})"
        range_rw = f" (hagati ya {number(n['reached_low'])} na {number(n['reached_high'])})"
        en = (
            f"{action_en} at {site_name}. About {reached} children{range_en if spread else ''} "
            f"would gain a place within a {catchment_minutes}-minute walk. About "
            f"{number(n['high_risk'])} of them are expected to be at risk of stunting. Mothers of "
            f"under-3s reached who say childcare keeps them from work: about "
            f"{number(n['mothers'])}. Main reasons: {reasons_en}. Estimated cost: {cost} RWF."
        )
        rw = (
            f"{action_rw} kuri {site_name}. Abana bagera kuri {reached}"
            f"{range_rw if spread else ''} babona umwanya mu rugendo rw'iminota "
            f"{catchment_minutes} n'amaguru. Abagera kuri {number(n['high_risk'])} muri bo "
            f"bashobora kugira ibyago byo kugwingira. Ababyeyi b'abana bari munsi y'imyaka 3 "
            f"bagezweho bavuga ko kurera abana bibabuza gukora: bagera kuri "
            f"{number(n['mothers'])}. Impamvu nyamukuru: {reasons_rw}. "
            f"Igiciro giteganyijwe: {cost} RWF."
        )
        return en, rw
