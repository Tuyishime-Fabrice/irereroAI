"""Facility points: health facilities from healthsites.io or HDX, and OSM schools and childcare."""

import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from irerero_contract.enums import FacilityKind, Origin
from pipelines.runs import CheckResult
from pipelines.sources.base import Loader, LoadReport
from pipelines.sources.readers import SchemaError, read_csv
from pipelines.sources.spec import Column, Dataset, ExpectedFile

LON, LAT = (28.8, 31.0), (-2.9, -1.0)
INSERT = text(
    """
    INSERT INTO facility (id, kind, name, sector_code, location, source, reference_year, origin,
        pipeline_run_id)
    SELECT :id, :kind, :name, s.code, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :source,
        :year, :origin, :run_id
    FROM admin_unit s
    WHERE s.level = 'sector' AND ST_Contains(s.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
    LIMIT 1
    """
)


def write_facilities(
    conn: Connection, dataset: Dataset, run_id: uuid.UUID, rows: Iterable[dict[str, Any]]
) -> int:
    """Points outside Rwanda's sectors are skipped. Health points from OSM are skipped when a
    dedicated health facility list is loaded, so they are not shown twice."""
    has_health_list = conn.execute(
        text("SELECT EXISTS (SELECT 1 FROM facility WHERE kind = 'health')")
    ).scalar_one()
    meta = {
        "source": dataset.title,
        "year": dataset.reference_year or 0,
        "origin": dataset.origin.value,
        "run_id": run_id,
    }
    written = 0
    for row in rows:
        if has_health_list and row["kind"] is FacilityKind.HEALTH:
            continue
        written += conn.execute(INSERT, row | {"kind": row["kind"].value} | meta).rowcount
    return written


class HealthFacilities(Loader):
    dataset = Dataset(
        key="health_facilities",
        title="Health facility locations",
        publisher="healthsites.io / Humanitarian Data Exchange",
        access="Open download",
        url="https://data.humdata.org/dataset/rwanda-healthsites",
        licence="ODbL 1.0",
        origin=Origin.PUBLIC,
        reference_year=2025,
        files=(ExpectedFile("health_facilities.csv", "csv", "One row per facility"),),
        columns=(
            Column("facility_id", "text", "Identifier in the source"),
            Column("name", "text", "Facility name", required=False),
            Column(
                "facility_type",
                "text",
                "hospital | health_centre | health_post | clinic, as published",
                required=False,
            ),
            Column("lon", "number", "Longitude, EPSG:4326"),
            Column("lat", "number", "Latitude, EPSG:4326"),
        ),
        level="point",
        joins_on="lon/lat; the sector is the one containing the point",
        used_by=("need map: health facility points near planned sites",),
        produces=("facility: health",),
        fallback="OpenStreetMap health points when the extract is loaded; otherwise none",
        optional=True,
    )

    def load(self, conn: Connection, folder: Path, run_id: uuid.UUID) -> LoadReport:
        file = self.dataset.files[0].name
        rows = read_csv(folder / file, self.dataset.columns)
        for i, row in enumerate(rows, start=2):
            if not (LON[0] <= row["lon"] <= LON[1] and LAT[0] <= row["lat"] <= LAT[1]):
                raise SchemaError(f"{file} line {i}: lon/lat is outside Rwanda (swapped?)")
        written = write_facilities(
            conn,
            self.dataset,
            run_id,
            (
                {
                    "id": f"hf-{row['facility_id']}",
                    "kind": FacilityKind.HEALTH,
                    "name": row["name"],
                    "lon": row["lon"],
                    "lat": row["lat"],
                }
                for row in rows
            ),
        )
        return LoadReport(
            {"facility": written},
            [CheckResult("inside_rwanda", written > 0, f"{written} of {len(rows)} placed")],
        )
