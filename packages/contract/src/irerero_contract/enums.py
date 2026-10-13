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


class MainProblem(StrEnum):
    NONE = "none"
    NO_FOOD = "no_food"
    NO_WATER = "no_water"
    CAREGIVER_ABSENT = "caregiver_absent"
    BUILDING_DAMAGE = "building_damage"
    WEATHER = "weather"
    OTHER = "other"


class ReportChannel(StrEnum):
    WEB = "web"
    OFFLINE = "offline"
    SMS = "sms"
    ASSISTED = "assisted"


class QualityFlag(StrEnum):
    """Set by validation. A flagged report is stored, shown to the officer, never dropped."""

    OUT_OF_RANGE_CONFIRMED = "out_of_range_confirmed"
    ENROLMENT_JUMP = "enrolment_jump"
    ATTENDANCE_JUMP = "attendance_jump"
    LATE_SUBMISSION = "late_submission"


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


class AlertKind(StrEnum):
    ATTENDANCE_DROP = "attendance_drop"
    MISSING_REPORT = "missing_report"
    OVERCROWDING = "overcrowding"
    WASH = "wash"
    CLOSURE_RISK = "closure_risk"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class DemandKind(StrEnum):
    EMPTY_SEARCH = "empty_search"
    CENTRE_REQUEST = "centre_request"


class Role(StrEnum):
    PARENT = "parent"
    CAREGIVER = "caregiver"
    SECTOR_OFFICER = "sector_officer"
    DISTRICT_PLANNER = "district_planner"
    NATIONAL_ANALYST = "national_analyst"
    ADMIN = "admin"


class ScopeLevel(StrEnum):
    NONE = "none"
    CENTRE = "centre"
    SECTOR = "sector"
    DISTRICT = "district"
    NATIONAL = "national"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EngineComponent(StrEnum):
    NEED = "need"
    COVERAGE = "coverage"
    OPTIMIZER = "optimizer"
    EARLY_WARNING = "early_warning"
    EXPLAINER = "explainer"


class SourceStatus(StrEnum):
    """Whether a source is loaded, or stood in for by simulated data until Phase 2."""

    LOADED = "loaded"
    SIMULATED_STAND_IN = "simulated_stand_in"
    PLANNED = "planned"
