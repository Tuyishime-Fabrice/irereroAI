"""All contract tables. Importing this module registers them on Base.metadata."""

from irerero_contract.tables.accounts import RefreshToken, UserAccount
from irerero_contract.tables.audit import AuditLog
from irerero_contract.tables.catalogue import DataSource, ModelVersion, PipelineRun
from irerero_contract.tables.centres import Centre
from irerero_contract.tables.demand import DemandSignal
from irerero_contract.tables.estimates import AreaIndicator, CoverageSnapshot, NeedEstimate
from irerero_contract.tables.geography import AdminUnit
from irerero_contract.tables.planning import (
    CandidateSite,
    Decision,
    PlanningDefault,
    Recommendation,
    Scenario,
    UnitCost,
)

__all__ = [
    "AdminUnit",
    "AreaIndicator",
    "AuditLog",
    "CandidateSite",
    "Centre",
    "CoverageSnapshot",
    "DataSource",
    "Decision",
    "DemandSignal",
    "ModelVersion",
    "NeedEstimate",
    "PipelineRun",
    "PlanningDefault",
    "Recommendation",
    "RefreshToken",
    "Scenario",
    "UnitCost",
    "UserAccount",
]
