"""ECD centres with capacity and enrolment: the NCDA ECD Mapping System export."""

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from irerero_contract.enums import CentreType, FeeBand, Origin
from pipelines.runs import CheckResult
from pipelines.sources.base import Loader, LoadReport
from pipelines.sources.readers import SchemaError, read_csv
from pipelines.sources.spec import Column, Dataset, ExpectedFile

FILE = "ecd_centres.csv"
TYPES = {t.value: t for t in CentreType}
# Enrolment above this multiple of capacity is treated as a typing error.
MAX_CROWDING = 3
INSERT = text(
    """
    INSERT INTO centre (code, name, type, status, sector_code, location, capacity, serves_0_2,
        serves_3_6, opening_hours, fee_band, offers_meals, offers_growth_monitoring,
        disability_inclusive, verified, water_available, enrolment, enrolment_as_of, ncda_ref,
        source, reference_year, origin, pipeline_run_id)
    SELECT :code, :name, :type, 'active', s.code, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
        :capacity, :serves_0_2, :serves_3_6, :opening_hours, :fee_band, :offers_meals,
        :offers_growth_monitoring, :disability_inclusive, :verified, :water_available,
        :enrolment, :enrolment_as_of, :ncda_ref, :source, :year, :origin, :run_id
    FROM admin_unit s
    WHERE s.level = 'sector' AND ST_Contains(s.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
    LIMIT 1
    """
)


def _type(raw: str, where: str) -> CentreType:
    key = raw.strip().lower().replace("-", "_").replace(" ", "_").removesuffix("_ecd")
    if key not in TYPES:
        raise SchemaError(f"{where}: centre_type must be one of {', '.join(TYPES)}")
    return TYPES[key]


class EcdCentres(Loader):
    dataset = Dataset(
        key="ecd_centres",
        title="NCDA ECD Mapping System: centres, capacity and enrolment",
        publisher="National Child Development Agency (NCDA)",
        access="Data sharing agreement with NCDA",
        url=None,
        licence="NCDA data sharing agreement; not for redistribution",
        origin=Origin.PARTNER,
        reference_year=2026,
        files=(ExpectedFile(FILE, "csv", "Centre register export, one row per centre"),),
        columns=(
            Column("centre_id", "text", "NCDA record id"),
            Column("name", "text", "Centre name as registered"),
            Column(
                "centre_type",
                "text",
                "home_based | community_based | school_based | centre_based",
            ),
            Column("lon", "number", "Longitude, EPSG:4326"),
            Column("lat", "number", "Latitude, EPSG:4326"),
            Column("capacity", "integer", "Children the centre can take"),
            Column("enrolment", "integer", "Children enrolled in the latest record"),
            Column("enrolment_as_of", "date", "Date of that record, YYYY-MM-DD"),
            Column("serves_0_2", "boolean", "Takes children aged 0 to 2: yes or no"),
            Column("serves_3_6", "boolean", "Takes children aged 3 to 6: yes or no"),
            Column("offers_meals", "boolean", "Serves at least one meal a day"),
            Column("water_available", "boolean", "Safe drinking water and handwashing on site"),
            Column("verified", "boolean", "Verified in the NCDA system", required=False),
            Column("opening_hours", "text", "e.g. Mo-Fr 07:30-12:00", required=False),
            Column(
                "fee_band",
                "text",
                "free | under_1000 | from_1000_to_5000 | over_5000 (RWF a month)",
                required=False,
            ),
            Column("offers_growth_monitoring", "boolean", "Growth monitoring", required=False),
            Column("disability_inclusive", "boolean", "Disability inclusive", required=False),
        ),
        level="point",
        joins_on="lon/lat; the sector is the one containing the point",
        used_by=(
            "catchments and coverage gaps",
            "optimizer: upgrade and support candidates, overcrowding",
            "parent page: nearest centres",
        ),
        produces=("centre", "candidate_site: upgrade and support options"),
        fallback="Simulated centres for Gicumbi, labelled simulated",
        notes=(
            "IrereroAI reads the NCDA register and never edits it. A later NCDA API can "
            "replace this file without changing anything downstream.",
        ),
    )

    def load(self, conn: Connection, folder: Path, run_id: uuid.UUID) -> LoadReport:
        rows = read_csv(folder / FILE, self.dataset.columns)
        seen: set[str] = set()
        records: list[dict[str, Any]] = []
        for i, row in enumerate(rows, start=2):
            where = f"{FILE} line {i}"
            ref = row["centre_id"]
            if ref in seen:
                raise SchemaError(f"{where}: centre_id {ref} appears twice")
            seen.add(ref)
            code = f"NCDA-{ref}"
            if len(code) > 32:
                raise SchemaError(f"{where}: centre_id is longer than 27 characters")
            if not (row["serves_0_2"] or row["serves_3_6"]):
                raise SchemaError(f"{where}: a centre must serve at least one age band")
            if row["enrolment"] > MAX_CROWDING * max(row["capacity"], 1):
                raise SchemaError(f"{where}: enrolment is over three times capacity")
            fee = row["fee_band"]
            if fee is not None and fee not in {f.value for f in FeeBand}:
                raise SchemaError(f"{where}: unknown fee_band {fee}")
            records.append(
                row
                | {
                    "code": code,
                    "ncda_ref": ref,
                    "type": _type(row["centre_type"], where).value,
                    "verified": bool(row["verified"]),
                    "source": self.dataset.title,
                    "year": self.dataset.reference_year,
                    "origin": self.dataset.origin.value,
                    "run_id": run_id,
                }
            )
        placed = sum(conn.execute(INSERT, record).rowcount for record in records)
        return LoadReport(
            {"centre": placed},
            [
                CheckResult("unique_ids", True, f"{len(records)} unique NCDA ids"),
                CheckResult(
                    "inside_rwanda", placed == len(records), f"{placed} placed in a sector"
                ),
            ],
        )
