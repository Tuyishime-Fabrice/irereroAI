"""Every fixed choice the demo story depends on, in one place."""

import random
import uuid
from datetime import date

SEED = 20260713
SOURCE = "IrereroAI demo generator (simulated)"
REFERENCE_YEAR = 2026

# Date of the simulated centre feed record, and the eight weeks of parent requests before it.
ENROLMENT_AS_OF = date(2026, 9, 21)
DEMAND_WEEKS = 8

DEMO_DISTRICT = "D-GICUMBI"
# The district town: denser population and more centres.
TOWN_SECTOR = "S-GICUMBI-BYUMBA"
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
