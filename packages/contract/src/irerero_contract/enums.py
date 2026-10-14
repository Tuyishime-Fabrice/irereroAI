"""Code lists shared by the database, the API, the engine adapters and the pipelines.

Values are stored as strings with CHECK constraints rather than native Postgres enums, so
Phase 2 can extend a list with a plain migration.
"""

from enum import StrEnum


class Origin(StrEnum):
    """Where a record comes from. The UI reads this to show badges and the simulated label."""

    OFFICIAL = "official"
    PUBLIC = "public"
    PARTNER = "partner"
    SIMULATED = "simulated"


class AdminLevel(StrEnum):
    COUNTRY = "country"
    PROVINCE = "province"
    DISTRICT = "district"
    SECTOR = "sector"
    CELL = "cell"
    VILLAGE = "village"


class CentreType(StrEnum):
    HOME_BASED = "home_based"
    COMMUNITY_BASED = "community_based"
    SCHOOL_BASED = "school_based"
    CENTRE_BASED = "centre_based"


class FeeBand(StrEnum):
    """Monthly fee per child in Rwandan francs."""

    FREE = "free"
    UNDER_1000 = "under_1000"
    FROM_1000_TO_5000 = "from_1000_to_5000"
    OVER_5000 = "over_5000"


class CentreStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class CandidateKind(StrEnum):
    VILLAGE = "village"
    SCHOOL = "school"
    CENTRE_UPGRADE = "centre_upgrade"
    CENTRE_SUPPORT = "centre_support"


class CostBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Action(StrEnum):
    BUILD = "build"
    UPGRADE = "upgrade"
    SUPPORT = "support"


class RecommendationStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class Verdict(StrEnum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class RejectionReason(StrEnum):
    """Each code maps to an optimizer constraint in the next run (see engine.optimizer)."""

    NO_LAND = "no_land"
    ALREADY_FUNDED = "already_funded"
    ACCESS_PROBLEM = "access_problem"
    COMMUNITY_OBJECTION = "community_objection"
    OTHER = "other"


class Role(StrEnum):
    """Signed-in roles. Parents use the public pages and never need an account."""

    DISTRICT_PLANNER = "district_planner"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EngineComponent(StrEnum):
    NEED = "need"
    COVERAGE = "coverage"
    OPTIMIZER = "optimizer"
    EXPLAINER = "explainer"


class SourceStatus(StrEnum):
    """Whether a source is loaded, or stood in for by simulated data until Phase 2."""

    LOADED = "loaded"
    SIMULATED_STAND_IN = "simulated_stand_in"
    PLANNED = "planned"
