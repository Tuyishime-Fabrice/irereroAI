"""RDHS 2025: stunting among children under 5, by district.

Typed from the report table, or tabulated by `make intake` from the DHS household-member recode
(RWPR..FL.dta) with the survey weights and design (basis = microdata, a model estimate). Only
the 30 district rates and their 95% intervals are staged; no child record leaves the intake."""

from pathlib import Path

from irerero.config import MODEL, PUBLISHED, RAW
from irerero.data.crosswalk import district_ids
from irerero.data.sources.base import Loaded, folder, status
from irerero.data.spec import DISTRICT_COLUMN, PAGE_COLUMN, Column, Dataset
from irerero.data.validate import read_csv

FILE = "rdhs_2025_stunting.csv"
REPORT, MICRODATA = "report", "microdata"
DATASET = Dataset(
    key="rdhs_2025",
    title="Rwanda Demographic and Health Survey 2025",
    publisher="NISR, Ministry of Health, The DHS Program",
    files=(FILE,),
    format="CSV typed from the report table, or tabulated from the DHS microdata by intake",
    columns=(
        *DISTRICT_COLUMN,
        Column("stunting_u5", "share", "Children under 5 below -2 SD height-for-age"),
        Column("stunting_u5_low", "share", "Lower 95% bound", required=False),
        Column("stunting_u5_high", "share", "Upper 95% bound", required=False),
        Column(
            "basis",
            "text",
            f"'{REPORT}' (typed from the report, the default) or '{MICRODATA}' (weighted from the "
            "DHS microdata by `make intake`)",
            required=False,
        ),
        PAGE_COLUMN,
    ),
    level="district",
    reference_period="2025",
    licence="Published report; cite NISR and The DHS Program",
    url="https://www.statistics.gov.rw",
    used_by=("DIAGNOSE: wellbeing (district context)", "LEARN: nutrition course trigger"),
    status=PUBLISHED,
    fallback="Simulated district values (seed 2026)",
    notes=(
        "Write 38.8% as 0.388.",
        "Or put the DHS household-member recode (RWPR91FL.dta from the microdata zip) through "
        "`make intake`: de facto children under 5 with a valid height-for-age z-score, stunted "
        "below -2 SD, weighted by hv005, 95% intervals from the strata and clusters.",
    ),
)


def load(raw: Path = RAW) -> Loaded:
    directory, real = folder(DATASET, raw)
    frame = read_csv(directory / FILE, DATASET.columns)
    frame["geo_id"] = district_ids(DATASET.key, frame.district_name)
    state = status(DATASET, real)
    if real and (frame.basis == MICRODATA).any():
        state = MODEL  # IrereroAI's tabulation, not a figure the DHS published
    return Loaded(frame, state, real, (directory / FILE,))
