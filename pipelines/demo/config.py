"""Every fixed choice the demo story depends on, in one place."""

import random
import uuid
from datetime import date, timedelta

SEED = 20260713
SOURCE = "IrereroAI demo generator (simulated)"
REFERENCE_YEAR = 2026

# Twelve reporting weeks. The demo's "current week" is week 12, whatever today's date is.
FIRST_WEEK = date(2026, 7, 6)
WEEKS = [FIRST_WEEK + timedelta(weeks=i) for i in range(12)]
CURRENT_WEEK = WEEKS[-1]

DEMO_DISTRICT = "D-GICUMBI"
OFFICER_SECTOR = "S-GICUMBI-BYUMBA"
UNDERSERVED_SECTOR = "S-GICUMBI-CYUMBA"

# Gicumbi stunting among children under 5, RDHS 2025 (figure supplied by the team).
# Sector values are simulated around it; the district value equals it.
GICUMBI_STUNTING = 0.388
GICUMBI_STUNTING_SOURCE = "RDHS 2025 district value 38.8%; sector split simulated"

NAMESPACE = uuid.UUID("5b0f1d8e-6a43-4c1e-9b8a-7f3e2d1c0a99")


def stable_id(*parts: object) -> uuid.UUID:
    """The same key gives the same id on every run, so links and tests stay valid."""
    return uuid.uuid5(NAMESPACE, ":".join(str(p) for p in parts))


def rng(name: str) -> random.Random:
    """One generator per module, so changing one module does not reshuffle the others."""
    return random.Random(f"{SEED}:{name}")


def slug(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in name.upper())
    return "-".join(part for part in cleaned.split("-") if part)
