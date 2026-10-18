"""Demo roles. Every user is invented; no real names or personal data. The selector is shown
only in demo mode and says so."""

from dataclasses import dataclass

PLANNER = "district_planner"
ANALYST = "national_analyst"
OFFICER = "sector_officer"
CAREGIVER = "caregiver"
ADMIN = "admin"

ROLE_LABELS = {
    PLANNER: "District planner",
    ANALYST: "National analyst",
    OFFICER: "Sector officer",
    CAREGIVER: "Caregiver / teacher",
    ADMIN: "Admin",
}


@dataclass(frozen=True)
class User:
    user_id: str
    role: str
    name: str
    district_id: str | None = None
    sector_id: str | None = None
    centre_id: str | None = None

    @property
    def can_decide(self) -> bool:
        """Approve, edit or reject plan items and set weights for their own district."""
        return self.role == PLANNER


DEMO_USERS = (
    User("demo-planner", PLANNER, "Demo planner (fictional)", district_id="D-MUHANGA"),
    User("demo-analyst", ANALYST, "Demo national analyst (fictional)"),
    User(
        "demo-officer",
        OFFICER,
        "Demo sector officer (fictional)",
        district_id="D-MUHANGA",
        sector_id="S-MUHANGA-CYEZA",
    ),
    User(
        "demo-caregiver",
        CAREGIVER,
        "Demo caregiver (fictional)",
        district_id="D-MUHANGA",
        sector_id="S-MUHANGA-CYEZA",
        centre_id="SIM-MUH-001",
    ),
    User("demo-admin", ADMIN, "Demo admin (fictional)"),
)
