"""The centres the demo story depends on. Everything else is generated around them."""

from dataclasses import dataclass

from irerero_contract.enums import CentreType


@dataclass(frozen=True)
class StoryCentre:
    role: str
    code: str
    name: str
    sector_code: str
    type: CentreType
    capacity: int
    note: str


STORY_CENTRES = (
    StoryCentre(
        "caregiver_home",
        "ECD-GIC-001",
        "Irerero Ineza",
        "S-GICUMBI-BYUMBA",
        CentreType.COMMUNITY_BASED,
        60,
        "The demo caregiver's centre. Clean history; this week's report is not in yet.",
    ),
    StoryCentre(
        "no_water",
        "ECD-GIC-002",
        "Irerero Umucyo",
        "S-GICUMBI-BYUMBA",
        CentreType.COMMUNITY_BASED,
        50,
        "Attendance drops for the last three weeks; the reports say there is no water.",
    ),
    StoryCentre(
        "overcrowded",
        "ECD-GIC-003",
        "Irerero Urumuri",
        "S-GICUMBI-BYUMBA",
        CentreType.CENTRE_BASED,
        60,
        "Enrolment well above capacity and a long, growing waiting list.",
    ),
    StoryCentre(
        "stopped_reporting",
        "ECD-GIC-004",
        "Irerero Amahoro",
        "S-GICUMBI-RUKOMO",
        CentreType.HOME_BASED,
        25,
        "Reports stop after week 9.",
    ),
    StoryCentre(
        "implausible_jump",
        "ECD-GIC-005",
        "Irerero Ubumwe",
        "S-GICUMBI-MUKARANGE",
        CentreType.COMMUNITY_BASED,
        45,
        "Week 9 enrolment more than doubles, then returns; the quality check flags it.",
    ),
    StoryCentre(
        "underserved",
        "ECD-GIC-006",
        "Urugo mbonezamikurire Cyumba",
        "S-GICUMBI-CYUMBA",
        CentreType.HOME_BASED,
        20,
        "The only centre in the under-served sector where parents ask for more.",
    ),
)

STORY_BY_ROLE = {c.role: c for c in STORY_CENTRES}
