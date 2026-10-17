"""Write docs/data_dictionary.md from the database models.

python -m irerero.docs --write    # regenerate
python -m irerero.docs --check    # fail if out of date
"""

import argparse
import sys

from irerero.config import ROOT
from irerero.db.models import ANALYSIS_TABLES, Base

DOC = ROOT / "docs" / "data_dictionary.md"
TABLES = {
    "geo_unit": "Country, provinces, districts and sectors. geo_id: RW, P-<NAME>, D-<NAME>, "
    "S-<DISTRICT>-<SECTOR>; nisr_code once the crosswalk is reviewed.",
    "source": "Every dataset, whether its real file was loaded, and its licence.",
    "observation": "Every input value: where, what, when, from which source and page, with its "
    "status. One row per geo_id, indicator and period.",
    "estimate_2026": "PLAN: children aged 3 to 5 in 2026 with a range, attendance, and the share "
    "more than 1 km from a school.",
    "model_run": "DIAGNOSE: each peer-model candidate with its cross-validation metrics; the "
    "chosen one also holds the diagnostics (coverage, Moran's I, error breakdowns).",
    "model_output": "DIAGNOSE: observed and expected attendance per sector with the 80% "
    "interval and top drivers (associations).",
    "diagnosis": "DIAGNOSE: five factor scores, the main bottleneck, the action and the reasons, "
    "at the default target.",
    "forecast": "TRACK: enrolment rate per district and nationally: observed years, projected "
    "years with a range, and the back-test.",
    "supply_extract": "NCDA ECD Mapping extract in the connector schema (simulated for Muhanga "
    "in the demo).",
    "course": "LEARN: the four courses, English and Kinyarwanda titles, trigger and source.",
    "lesson": "LEARN: lesson text (Markdown) per course.",
    "quiz_item": "LEARN: five quiz questions per course.",
    "app_user": "Users and roles (demo users are fictional).",
    "plan": "TRACK: a district plan with its target and priority weights.",
    "plan_item": "TRACK: one recommendation in a plan, its decision, reason and status.",
    "centre_checkin": "LEARN: monthly centre check-in, counts only.",
    "assignment": "LEARN: a course for a caregiver: trigger, who made it required, due date, "
    "progress and score (private to the caregiver).",
    "audit_log": "Append-only record of every decision, status change, confirmation and "
    "check-in: who, when, before, after, why.",
}


def document() -> str:
    analysis = {t.__tablename__ for t in ANALYSIS_TABLES}
    lines = [
        "# Data dictionary",
        "",
        "Generated from `irerero/db/models.py` by `python -m irerero.docs --write`; do not edit "
        "by hand. Analysis tables are rebuilt by `make data`; app tables keep their rows.",
    ]
    for name, table in Base.metadata.tables.items():
        kind = "analysis" if name in analysis else "app"
        lines += ["", f"## `{name}` ({kind})", "", TABLES.get(name, ""), ""]
        lines += ["| Column | Type | Null | Key |", "| --- | --- | --- | --- |"]
        for c in table.columns:
            key = (
                "primary"
                if c.primary_key
                else (f"→ {next(iter(c.foreign_keys)).target_fullname}" if c.foreign_keys else "")
            )
            lines.append(f"| `{c.name}` | {c.type} | {'yes' if c.nullable else 'no'} | {key} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = document()
    if args.check:
        if not DOC.exists() or DOC.read_text() != text:
            print("docs/data_dictionary.md is out of date: run python -m irerero.docs --write")
            return 1
        return 0
    DOC.parent.mkdir(exist_ok=True)
    DOC.write_text(text)
    print(f"wrote {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
