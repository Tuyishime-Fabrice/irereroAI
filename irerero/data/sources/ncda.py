"""NCDA ECD Mapping System extract, in the supply_extract schema.

Not available to the team: a simulated Muhanga file (seed 2026) stands in. IrereroAI reads
this file and never edits NCDA records; an NCDA API can later write the same schema.
"""

from pathlib import Path

from irerero.config import OBSERVED, RAW
from irerero.data.crosswalk import sector_ids
from irerero.data.sources.base import Loaded, folder, status
from irerero.data.spec import NAME_COLUMNS, Column, Dataset
from irerero.data.validate import SchemaError, read_csv

FILE = "supply_extract.csv"
TYPES = {"home_based", "community_based", "school_based", "centre_based"}
DATASET = Dataset(
    key="ncda",
    title="NCDA ECD Mapping System extract (supply_extract schema)",
    publisher="National Child Development Agency (NCDA)",
    files=(FILE,),
    format="CSV in the supply_extract schema",
    columns=(
        Column("centre_id", "text", "NCDA centre id"),
        Column("name", "text", "Centre name"),
        Column("centre_type", "text", "home_based | community_based | school_based | centre_based"),
        *NAME_COLUMNS,
        Column("lon", "longitude", "Longitude (WGS84)"),
        Column("lat", "latitude", "Latitude (WGS84)"),
        Column("capacity", "integer", "Places"),
        Column("enrolled_3_5", "integer", "Children aged 3 to 5 enrolled"),
        Column("caregivers", "integer", "Caregivers"),
        Column("as_of", "date", "Date of the record, YYYY-MM-DD"),
    ),
    level="centre",
    reference_period="as_of date",
    licence="NCDA data sharing agreement",
    url=None,
    used_by=(
        "LEARN: centres and caregivers in the pilot",
        "Data and methods: optional supply connector (off by default)",
    ),
    status=OBSERVED,
    fallback="Simulated Muhanga extract (seed 2026)",
    notes=(
        "Never added to census or MINEDUC enrolment: NCDA counts include home-based ECD, the "
        "formal pre-primary measure does not.",
    ),
)


def load(raw: Path = RAW) -> Loaded:
    directory, real = folder(DATASET, raw)
    frame = read_csv(directory / FILE, DATASET.columns)
    if not frame.centre_type.isin(TYPES).all():
        raise SchemaError(f"{FILE}: centre_type must be one of {sorted(TYPES)}")
    if frame.centre_id.duplicated().any():
        raise SchemaError(f"{FILE}: centre_id must be unique")
    frame["geo_id"] = sector_ids(DATASET.key, frame.district_name, frame.sector_name)
    return Loaded(frame, status(DATASET, real), real, (directory / FILE,))
