"""EICV7 district presentations: poverty, by sector where published, else by district."""

from pathlib import Path

import pandas as pd

from irerero.config import PUBLISHED, RAW
from irerero.data.crosswalk import district_ids, sector_ids
from irerero.data.sources.base import Loaded, folder, status
from irerero.data.spec import PAGE_COLUMN, Column, Dataset
from irerero.data.validate import SchemaError, read_csv

FILE = "eicv7_poverty.csv"
DATASET = Dataset(
    key="eicv7",
    title="Integrated Household Living Conditions Survey 7 (EICV7), 2023/24",
    publisher="NISR",
    files=(FILE,),
    format="CSV typed from the district presentations",
    columns=(
        Column("level", "text", "sector or district"),
        Column("district_name", "text", "District name as printed"),
        Column("sector_name", "text", "Sector name, for sector rows", required=False),
        Column("poverty_rate", "share", "Share of people below the national poverty line"),
        PAGE_COLUMN,
    ),
    level="sector if published, otherwise district",
    reference_period="2023/24",
    licence="NISR publication; cite NISR EICV7",
    url="https://www.statistics.gov.rw",
    used_by=("PLAN: poverty component of the priority index", "DIAGNOSE: poverty factor"),
    status=PUBLISHED,
    fallback="Simulated sector values (seed 2026)",
)


def load(raw: Path = RAW) -> Loaded:
    directory, real = folder(DATASET, raw)
    frame = read_csv(directory / FILE, DATASET.columns)
    if not frame.level.isin({"sector", "district"}).all():
        raise SchemaError(f"{FILE}: level must be sector or district")
    sector = frame.level == "sector"
    ids = pd.Series(index=frame.index, dtype="object")
    if sector.any():
        ids[sector] = sector_ids(
            DATASET.key, frame.district_name[sector], frame.sector_name[sector]
        )
    if (~sector).any():
        ids[~sector] = district_ids(DATASET.key, frame.district_name[~sector])
    frame["geo_id"] = ids
    return Loaded(frame, status(DATASET, real), real, (directory / FILE,))
