"""The source catalogue the methodology page reads: what is loaded, simulated or not loaded."""

from collections.abc import Set

from sqlalchemy import Connection, insert

from irerero_contract.enums import EngineComponent, Origin, SourceStatus
from irerero_contract.tables import DataSource, ModelVersion, PlanningDefault
from pipelines.demo.need import MODEL_VERSION as NEED_MODEL_VERSION
from pipelines.sources import DATASETS
from pipelines.sources.boundaries import SOURCE as BOUNDARY_SOURCE

# Datasets whose part the demo generator plays, with simulated values, until they are loaded.
STOOD_IN = {"census_2022", "eicv7", "lfs_2025", "rdhs_2025", "ecd_centres"}


def load_catalogue(conn: Connection, present: Set[str]) -> int:
    simulated = ["need_estimate", "candidate_site", "unit_cost", "demand_signal"]
    if "ecd_centres" not in present:
        simulated.insert(0, "centre")
    rows = [
        {
            "id": "demo_generator",
            "name": "IrereroAI demo generator",
            "publisher": "IrereroAI",
            "reference_year": 2026,
            "origin": Origin.SIMULATED,
            "status": SourceStatus.LOADED,
            "licence": "Simulated data, no real people or centres",
            "url": None,
            "feeds": simulated,
        }
    ]
    if "boundaries" not in present:
        rows.append(
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
            }
        )
    for dataset in DATASETS:
        if dataset.key in present:
            status = SourceStatus.LOADED
        elif dataset.key in STOOD_IN:
            status = SourceStatus.SIMULATED_STAND_IN
        else:
            status = SourceStatus.PLANNED
        rows.append(
            {
                "id": dataset.key,
                "name": dataset.title,
                "publisher": dataset.publisher,
                "reference_year": dataset.reference_year,
                "origin": dataset.origin,
                "status": status,
                "licence": dataset.licence,
                "url": dataset.url,
                "feeds": list(dataset.produces),
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
