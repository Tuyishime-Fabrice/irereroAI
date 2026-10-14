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
    enrolment: int
    water_available: bool
    note: str


STORY_CENTRES = (
    StoryCentre(
        "steady",
        "ECD-GIC-001",
        "Irerero Ineza",
        "S-GICUMBI-BYUMBA",
        CentreType.COMMUNITY_BASED,
        60,
        52,
        True,
        "A well-run centre with a few free places.",
    ),
    StoryCentre(
        "no_water",
        "ECD-GIC-002",
        "Irerero Umucyo",
        "S-GICUMBI-BYUMBA",
        CentreType.COMMUNITY_BASED,
        50,
        44,
        False,
        "No safe water on site: a support candidate.",
    ),
    StoryCentre(
        "overcrowded",
        "ECD-GIC-003",
        "Irerero Urumuri",
        "S-GICUMBI-BYUMBA",
        CentreType.CENTRE_BASED,
        60,
        81,
        True,
        "Enrolment well above capacity: highlighted on the coverage gap view.",
    ),
    StoryCentre(
        "outgrown_home",
        "ECD-GIC-004",
        "Irerero Amahoro",
        "S-GICUMBI-RUKOMO",
        CentreType.HOME_BASED,
        25,
        33,
        True,
        "A home-based centre that has outgrown its space: an upgrade candidate.",
    ),
    StoryCentre(
        "steady_rural",
        "ECD-GIC-005",
        "Irerero Ubumwe",
        "S-GICUMBI-MUKARANGE",
        CentreType.COMMUNITY_BASED,
        45,
        38,
        True,
        "A steady rural centre.",
    ),
    StoryCentre(
        "underserved",
        "ECD-GIC-006",
        "Urugo mbonezamikurire Cyumba",
        "S-GICUMBI-CYUMBA",
        CentreType.HOME_BASED,
        20,
        22,
        True,
        "The only centre in the under-served sector where parents ask for more.",
    ),
)

STORY_BY_CODE = {c.code: c for c in STORY_CENTRES}
