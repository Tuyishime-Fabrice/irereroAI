"""NCDA ECD Mapping System extract, in the supply_extract schema.

`make intake` converts the NCDA extract (ncda_ecd_mapping_extract.csv) to this schema. The
extract carries no capacity and counts children aged 3 to 6, not 3 to 5, so `capacity` and
`enrolled_3_5` stay empty for it and `enrolled_3_6` holds its count: nothing is derived.
IrereroAI reads this file and never edits NCDA records; an NCDA API can later write the same
schema.

The simulated Muhanga centres (seed 2026) are the LEARN demonstration: they stand in while no
extract is staged, and in demo mode they are added beside a real extract, every row labelled
simulated, so the fictional caregivers keep their centres.
"""

from pathlib import Path

import pandas as pd

from irerero.config import DEMO, OBSERVED, RAW, SIMULATED
from irerero.data.crosswalk import sector_ids
from irerero.data.sources.base import Loaded, folder, status
from irerero.data.spec import NAME_COLUMNS, Column, Dataset
from irerero.data.validate import SchemaError, read_csv
from irerero.roles import demo_mode

FILE = "supply_extract.csv"
TYPES = {"home_based", "community_based", "school_based", "centre_based", "other", "not_stated"}
DATASET = Dataset(
    key="ncda",
    title="NCDA ECD Mapping System extract (supply_extract schema)",
    publisher="National Child Development Agency (NCDA)",
    files=(FILE,),
    format="CSV in the supply_extract schema",
    columns=(
        Column("centre_id", "text", "NCDA centre id"),
        Column("name", "text", "Centre name"),
        Column(
            "centre_type",
            "text",
            "home_based | community_based | school_based | centre_based | other | not_stated",
        ),
        *NAME_COLUMNS,
        Column("lon", "longitude", "Longitude (WGS84)"),
        Column("lat", "latitude", "Latitude (WGS84)"),
        Column("capacity", "integer", "Places (not in the NCDA extract)", required=False),
        Column("enrolled_3_5", "integer", "Children aged 3 to 5 enrolled", required=False),
        Column("enrolled_3_6", "integer", "Children aged 3 to 6 enrolled (NCDA)", required=False),
        Column("caregivers", "integer", "Caregivers", required=False),
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
        "Put ncda_ecd_mapping_extract.csv through `make intake`: it keeps active services, maps "
        "settings_types to centre_type and writes this file. Rows are shown on screen only when "
        "IRERERO_NCDA_DISPLAY is on (the data-sharing agreement must allow it).",
    ),
)


def _read(directory: Path) -> pd.DataFrame:
    frame = read_csv(directory / FILE, DATASET.columns)
    if not frame.centre_type.isin(TYPES).all():
        raise SchemaError(f"{FILE}: centre_type must be one of {sorted(TYPES)}")
    if frame.centre_id.duplicated().any():
        raise SchemaError(f"{FILE}: centre_id must be unique")
    frame["geo_id"] = sector_ids(DATASET.key, frame.district_name, frame.sector_name)
    return frame


def load(raw: Path = RAW, demo: bool | None = None) -> Loaded:
    """The extract, each row with its own `status`. In demo mode a real extract is joined by
    the simulated Muhanga demonstration centres, which keep the status simulated."""
    directory, real = folder(DATASET, raw)
    frame = _read(directory).assign(status=status(DATASET, real))
    files = (directory / FILE,)
    if real and (demo_mode() if demo is None else demo):
        extra = _read(DEMO / DATASET.key).assign(status=SIMULATED)
        clash = set(extra.centre_id) & set(frame.centre_id)
        if clash:
            raise SchemaError(f"{FILE}: demo centre ids also in the extract: {sorted(clash)[:5]}")
        frame = pd.concat([frame, extra], ignore_index=True)
        files += (DEMO / DATASET.key / FILE,)
    return Loaded(frame, status(DATASET, real), real, files)
