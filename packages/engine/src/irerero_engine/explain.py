"""Explainer: plain-language explanations in English and Kinyarwanda from drivers and numbers.

Phase 1 baseline: templates. Phase 2: SHAP drivers feed the same templates, and a
retrieval-grounded assistant answers follow-up questions (see assistant.py).

Kinyarwanda templates are drafts until reviewed; all are listed in docs/i18n-review.md.
"""

from collections.abc import Mapping, Sequence
from typing import Protocol

from irerero_engine.types import Driver

PROBLEMS = {
    "none": ("none", "nta kibazo"),
    "no_food": ("no food", "nta biryo"),
    "no_water": ("no water", "nta mazi"),
    "caregiver_absent": ("caregiver absent", "umurezi ntiyaje"),
    "building_damage": ("building damage", "inyubako yangiritse"),
    "weather": ("bad weather", "ikirere kibi"),
    "other": ("other", "ibindi"),
}

ACTIONS = {
    "build": ("Build a new centre", "Kubaka irerero rishya"),
    "upgrade": ("Upgrade the home-based centre", "Kuzamura urugo mbonezamikurire"),
    "support": ("Support quality", "Gushyigikira ireme"),
}


def number(value: float) -> str:
    return f"{round(value):,}"


def percent(share: float | int | str) -> str:
    return f"{round(float(share) * 100)}%"


def alert_reason(
    kind: str, name: str, evidence: Mapping[str, float | int | str]
) -> tuple[str, str]:
    e = evidence
    if kind == "attendance_drop":
        en = (
            f"Attendance at {name} fell to {e['attendance']} of {e['enrolled']} children "
            f"({percent(e['rate'])}), against a usual {percent(e['usual_rate'])}, "
            f"for {e['weeks']} weeks in a row."
        )
        rw = (
            f"Ubwitabire kuri {name} bwagabanutse bugera ku bana {e['attendance']} kuri "
            f"{e['enrolled']} ({percent(e['rate'])}), mu gihe busanzwe ari "
            f"{percent(e['usual_rate'])}, mu byumweru {e['weeks']} bikurikirana."
        )
        problem = str(e.get("main_problem", "none"))
        if problem != "none":
            en += f" The reports give the main problem as: {PROBLEMS[problem][0]}."
            rw += f" Raporo zivuga ko ikibazo nyamukuru ari: {PROBLEMS[problem][1]}."
        return en, rw
    if kind == "missing_report":
        en = f"{name} has not sent a report for {e['weeks_missing']} weeks."
        rw = f"{name} imaze ibyumweru {e['weeks_missing']} itohereza raporo."
        if "last_report" in e:
            en += f" Last report: week of {e['last_report']}."
            rw += f" Raporo iheruka: icyumweru cyatangiye ku wa {e['last_report']}."
        return en, rw
    if kind == "overcrowding":
        return (
            f"{name} has {e['attendance']} children attending for {e['capacity']} places, "
            f"and {e['waiting_list']} on the waiting list.",
            f"{name} ifite abana {e['attendance']} bitabira mu myanya {e['capacity']}, "
            f"n'abandi {e['waiting_list']} bategereje.",
        )
    if kind == "wash":
        return (
            f"{name} reported no water or handwashing for {e['weeks']} week(s) in a row.",
            f"{name} yatangaje ko nta mazi cyangwa aho gukarabira bihari mu byumweru "
            f"{e['weeks']} bikurikirana.",
        )
    if kind == "closure_risk":
        problem = str(e["main_problem"])
        return (
            f"{name} may close: open {e['days_open']} days this week; main problem: "
            f"{PROBLEMS[problem][0]}.",
            f"{name} ishobora gufunga: yafunguye iminsi {e['days_open']} iki cyumweru; "
            f"ikibazo nyamukuru: {PROBLEMS[problem][1]}.",
        )
    raise ValueError(f"no reason template for alert kind {kind}")


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
        en = (
            f"{action_en} at {site_name}. About {number(n['reached'])} children (between "
            f"{number(n['reached_low'])} and {number(n['reached_high'])}) would gain a place "
            f"within a {catchment_minutes}-minute walk. About {number(n['high_risk'])} of them "
            f"are expected to be at risk of stunting, and {number(n['mothers'])} of their mothers "
            f"say childcare keeps them from work. Main reasons: {reasons_en}. "
            f"Estimated cost: {cost} RWF."
        )
        rw = (
            f"{action_rw} kuri {site_name}. Abana bagera kuri {number(n['reached'])} (hagati ya "
            f"{number(n['reached_low'])} na {number(n['reached_high'])}) babona umwanya mu "
            f"rugendo rw'iminota {catchment_minutes} n'amaguru. Abagera kuri "
            f"{number(n['high_risk'])} muri bo bashobora kugira ibyago byo kugwingira, kandi "
            f"ababyeyi babo {number(n['mothers'])} bavuga ko kurera abana bibabuza gukora. "
            f"Impamvu nyamukuru: {reasons_rw}. Igiciro giteganyijwe: {cost} RWF."
        )
        return en, rw
