"""The source catalogue the methodology page reads: what is loaded, simulated or planned."""

from sqlalchemy import Connection, insert

from irerero_contract.enums import EngineComponent, Origin, SourceStatus
from irerero_contract.tables import DataSource, ModelVersion, PlanningDefault
from pipelines.demo.geography import SOURCE as BOUNDARY_SOURCE
from pipelines.demo.need import MODEL_VERSION as NEED_MODEL_VERSION
from pipelines.registry import ADAPTERS

# Phase 2 sources whose role the demo generator fills with simulated values today.
STOOD_IN = {
    "census_2022": "child counts per sector",
    "rdhs_2025": "stunting risk per sector, around the published Gicumbi value",
    "lfs_2025": "mothers' childcare barrier share",
    "ncda_mapping": "centres and twelve weeks of weekly reports",
    "education_yearbook": "school candidate sites",
}


def load_catalogue(conn: Connection) -> int:
    rows = [
        {
            "id": "geoboundaries",
            "name": "geoBoundaries gbOpen, Rwanda provinces, districts and sectors",
            "publisher": "geoBoundaries (William & Mary), from NISR open data",
            "reference_year": 2023,
            "origin": Origin.PUBLIC,
            "status": SourceStatus.LOADED,
            "licence": "CC BY 4.0",
            "url": "https://www.geoboundaries.org",
            "feeds": ["admin_unit"],
        },
        {
            "id": "demo_generator",
            "name": "IrereroAI demo generator",
            "publisher": "IrereroAI",
            "reference_year": 2026,
            "origin": Origin.SIMULATED,
            "status": SourceStatus.LOADED,
            "licence": "Simulated data, no real people or centres",
            "url": None,
            "feeds": [
                "centre",
                "weekly_report",
                "need_estimate",
                "candidate_site",
                "unit_cost",
                "demand_signal",
            ],
        },
    ]
    for name, adapter in ADAPTERS.items():
        spec = adapter.spec
        status = SourceStatus.SIMULATED_STAND_IN if name in STOOD_IN else SourceStatus.PLANNED
        rows.append(
            {
                "id": name,
                "name": spec.title,
                "publisher": spec.publisher,
                "reference_year": spec.reference_year,
                "origin": spec.origin,
                "status": status,
                "licence": spec.licence,
                "url": spec.url,
                "feeds": list(spec.target_tables) + list(spec.indicators),
            }
        )
    conn.execute(insert(DataSource), rows)
    return len(rows)


def load_need_model(conn: Connection) -> None:
    conn.execute(
        insert(ModelVersion).values(
            id=NEED_MODEL_VERSION,
            component=EngineComponent.NEED,
            description=(
                "Simulated sector need written by the demo generator, with intervals. "
                "Phase 2 replaces it with a small-area model calibrated to official totals."
            ),
            params={"boundaries": BOUNDARY_SOURCE},
            metrics={},
        )
    )


def load_planning_defaults(conn: Connection) -> None:
    """Simulated defaults so the plan workspace opens with sensible values."""
    conn.execute(
        insert(PlanningDefault),
        [
            {
                "area_code": code,
                "budget_rwf": 120_000_000,
                "weight_stunting": 0.4,
                "weight_readiness": 0.4,
                "weight_jobs": 0.2,
            }
            for code in ("RW", "D-GICUMBI")
        ],
    )
