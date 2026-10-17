"""RDHS 2025 report tables: stunting among children under 5, by district."""

from pathlib import Path

from irerero.config import PUBLISHED, RAW
from irerero.data.crosswalk import district_ids
from irerero.data.sources.base import Loaded, folder, status
from irerero.data.spec import DISTRICT_COLUMN, PAGE_COLUMN, Column, Dataset
from irerero.data.validate import read_csv

FILE = "rdhs_2025_stunting.csv"
DATASET = Dataset(
    key="rdhs_2025",
    title="Rwanda Demographic and Health Survey 2025",
    publisher="NISR, Ministry of Health, The DHS Program",
    files=(FILE,),
    format="CSV typed from the report table",
    columns=(
        *DISTRICT_COLUMN,
        Column("stunting_u5", "share", "Children under 5 below -2 SD height-for-age"),
        Column("stunting_u5_low", "share", "Lower 95% bound", required=False),
        Column("stunting_u5_high", "share", "Upper 95% bound", required=False),
        PAGE_COLUMN,
    ),
    level="district",
    reference_period="2025",
    licence="Published report; cite NISR and The DHS Program",
    url="https://www.statistics.gov.rw",
    used_by=("DIAGNOSE: wellbeing (district context)", "LEARN: nutrition course trigger"),
    status=PUBLISHED,
    fallback="Simulated district values (seed 2026)",
    notes=("Write 38.8% as 0.388.",),
)


def load(raw: Path = RAW) -> Loaded:
    directory, real = folder(DATASET, raw)
    frame = read_csv(directory / FILE, DATASET.columns)
    frame["geo_id"] = district_ids(DATASET.key, frame.district_name)
    return Loaded(frame, status(DATASET, real), real, (directory / FILE,))
