"""Plain-language labels for every driver the engine can report.

Kinyarwanda labels are drafts until reviewed; every one is listed in docs/i18n-review.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    key: str
    label_en: str
    label_rw: str


FEATURES: dict[str, Feature] = {
    f.key: f
    for f in (
        Feature(
            "children_density",
            "Many young children per km²",
            "Abana bato benshi kuri kilometero kare",
        ),
        Feature(
            "uncovered_children",
            "Many children without a place nearby",
            "Abana benshi badafite umwanya hafi",
        ),
        Feature(
            "distance_to_centre",
            "Long walk to the nearest centre",
            "Urugendo rurerure ugana ku irerero riri hafi",
        ),
        Feature("stunting_risk", "High stunting risk", "Ibyago byinshi byo kugwingira"),
        Feature(
            "mothers_barrier",
            "Mothers say childcare keeps them from work",
            "Ababyeyi bavuga ko kurera abana bibabuza gukora",
        ),
        Feature("poverty", "High poverty", "Ubukene bwinshi"),
        Feature(
            "parent_demand", "Parents asked for a centre here", "Ababyeyi basabye irerero hano"
        ),
        Feature(
            "overcrowding", "Nearby centres are overcrowded", "Amarerero ari hafi yuzuye cyane"
        ),
        Feature("low_meal_coverage", "Few centres serve meals", "Amarerero make atanga amafunguro"),
        Feature(
            "report_problems",
            "Recent reports show problems",
            "Raporo za vuba zigaragaza ibibazo",
        ),
        Feature("low_cost", "Low cost per child reached", "Igiciro gito ku mwana umwe ugezweho"),
    )
}
