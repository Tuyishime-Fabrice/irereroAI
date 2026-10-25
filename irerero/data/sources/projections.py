"""NISR subnational population projections 2023 to 2032, by district."""

from pathlib import Path

from irerero.config import PUBLISHED, RAW
from irerero.data.crosswalk import district_ids
from irerero.data.sources.base import Loaded, folder, status
from irerero.data.spec import DISTRICT_COLUMN, PAGE_COLUMN, Column, Dataset
from irerero.data.validate import read_csv

FILE = "nisr_projections_2023_2032.csv"
DATASET = Dataset(
    key="projections",
    title="Rwanda Subnational Population Projections 2023-2032",
    publisher="NISR",
    files=(FILE,),
    format="CSV typed from the published tables",
    columns=(
        *DISTRICT_COLUMN,
        Column("year", "integer", "Projection year"),
        Column("population", "integer", "Projected population, medium variant"),
        Column("population_low", "integer", "Low variant", required=False),
        Column("population_high", "integer", "High variant", required=False),
        Column(
            "children_3_5",
            "integer",
            "Projected children aged 3 to 5 (from the single-age tables), medium variant",
            required=False,
        ),
        PAGE_COLUMN,
    ),
    level="district",
    reference_period="2023 to 2032",
    licence="NISR publication; cite NISR",
    url="https://www.statistics.gov.rw",
    used_by=("PLAN: calibrate the 2026 estimate", "TRACK: population for enrolment rates"),
    status=PUBLISHED,
    fallback="Simulated district projections (seed 2026)",
    notes=(
        "With children_3_5 (the single-age tables give it), the 2026 estimate takes each "
        "district's children aged 3 to 5 straight from the projection; without it, from the "
        "projected population and the census 2022 age share.",
    ),
)


def load(raw: Path = RAW) -> Loaded:
    directory, real = folder(DATASET, raw)
    frame = read_csv(directory / FILE, DATASET.columns)
    frame["geo_id"] = district_ids(DATASET.key, frame.district_name)
    return Loaded(frame, status(DATASET, real), real, (directory / FILE,))
