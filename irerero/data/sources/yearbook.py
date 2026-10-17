"""MINEDUC Education Statistical Yearbooks 2020/21 to 2024/25: pre-primary by district."""

from pathlib import Path

from irerero.config import OBSERVED, RAW, YEARBOOK_YEARS
from irerero.data.crosswalk import district_ids
from irerero.data.sources.base import Loaded, folder, status
from irerero.data.spec import DISTRICT_COLUMN, PAGE_COLUMN, Column, Dataset
from irerero.data.validate import SchemaError, read_csv

FILE = "mineduc_yearbook_preprimary.csv"
DATASET = Dataset(
    key="yearbook",
    title="Education Statistical Yearbooks 2020/21 to 2024/25 (pre-primary)",
    publisher="Ministry of Education (MINEDUC)",
    files=(FILE,),
    format="CSV typed from the yearbook district tables",
    columns=(
        *DISTRICT_COLUMN,
        Column("school_year", "text", "2020/21 ... 2024/25"),
        Column("pupils", "integer", "Pre-primary pupils"),
        Column("schools", "integer", "Schools with pre-primary"),
        Column("classrooms", "integer", "Pre-primary classrooms"),
        Column("teachers", "integer", "Pre-primary teachers"),
        Column("qualified_teachers", "integer", "Of them, qualified"),
        PAGE_COLUMN,
    ),
    level="district",
    reference_period="2020/21 to 2024/25",
    licence="MINEDUC publication; cite the yearbook and year",
    url="https://www.mineduc.gov.rw",
    used_by=("TRACK: enrolment trend to 2029", "DIAGNOSE: capacity (ratios, qualifications)"),
    status=OBSERVED,
    fallback="Simulated district series (seed 2026)",
)


def load(raw: Path = RAW) -> Loaded:
    directory, real = folder(DATASET, raw)
    frame = read_csv(directory / FILE, DATASET.columns)
    unknown = sorted(set(frame.school_year) - set(YEARBOOK_YEARS))
    if unknown:
        raise SchemaError(f"{FILE}: school_year must be one of {YEARBOOK_YEARS}, got {unknown}")
    frame["geo_id"] = district_ids(DATASET.key, frame.district_name)
    return Loaded(frame, status(DATASET, real), real, (directory / FILE,))
