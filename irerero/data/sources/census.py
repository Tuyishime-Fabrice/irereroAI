"""NISR Census 2022 district profiles: children 3 to 5 attending and never attended (Table
2.5), population, urban share, water, sanitation, electricity and education, by sector."""

from pathlib import Path

import pandas as pd

from irerero.config import MODEL, OBSERVED, RAW
from irerero.data.crosswalk import district_ids, sector_ids
from irerero.data.sources.base import Loaded, folder, status
from irerero.data.sources.census_pdf import parse_profiles
from irerero.data.spec import DISTRICT_COLUMN, NAME_COLUMNS, PAGE_COLUMN, Column, Dataset
from irerero.data.validate import SchemaError, read_csv

# Table 2.5 is required; the other tables fill the remaining columns when they are parsed or
# typed, and the factors that use them are left out while they are empty.
COUNTS = (
    Column("children_3_5", "integer", "Children aged 3 to 5 (Table 2.5 total)"),
    Column("children_3_5_attending", "integer", "Of them, attending nursery school (Table 2.5)"),
    Column("children_3_5_never_attended", "integer", "Of them, never attended (Table 2.5)"),
    Column("population", "integer", "Resident population", required=False),
    Column("children_0_4", "integer", "Children aged 0 to 4", required=False),
    Column("households", "integer", "Private households", required=False),
    Column(
        "hh_improved_water", "integer", "Households using an improved water source", required=False
    ),
    Column(
        "hh_improved_sanitation", "integer", "Households with improved sanitation", required=False
    ),
    Column("hh_electricity", "integer", "Households with electricity", required=False),
)
# How the counts were obtained. Printed Table 2.5 counts are observed; counts weighted from
# census sample records (one row per child) are IrereroAI's tabulation, a model estimate.
TABLE, SAMPLE = "table", "sample"
BASIS = Column(
    "basis",
    "text",
    f"'{TABLE}' (printed Table 2.5, the default) or '{SAMPLE}' (weighted from census sample "
    "records by `make intake`)",
    required=False,
)
SECTOR_COLUMNS = (
    *NAME_COLUMNS,
    *COUNTS,
    Column("urban_share", "share", "Share of the population living in urban areas", required=False),
    Column(
        "women_secondary_share",
        "share",
        "Women aged 15+ with secondary education or more (proxy for mothers' education)",
        required=False,
    ),
    BASIS,
    PAGE_COLUMN,
)
DISTRICT_COLUMNS = (*DISTRICT_COLUMN, *COUNTS, PAGE_COLUMN)

DATASET = Dataset(
    key="census_2022",
    title="Fifth Population and Housing Census (PHC5) 2022, district profiles",
    publisher="NISR",
    files=("census_2022_sectors.csv", "census_2022_districts.csv"),
    format="CSV (or the 30 district profile PDFs, parsed into these two CSVs)",
    columns=SECTOR_COLUMNS,
    level="sector, with district totals for checking",
    reference_period="2022 (census night 15 August 2022)",
    licence="NISR publication; cite NISR PHC5 2022",
    url="https://www.statistics.gov.rw/publication/2093",
    used_by=("PLAN: 2026 estimate, gap, priority", "DIAGNOSE: home environment, peer model"),
    status=OBSERVED,
    fallback="Simulated sector table for all 416 sectors (seed 2026)",
    notes=(
        "Put the 30 district profile PDFs in data/raw/census_2022/pdf/ and run `make data`: "
        "Table 2.5 and the other tables are parsed into the two CSVs in data/interim/. Or type "
        "the CSVs directly into data/raw/census_2022/.",
        "census_2022_districts.csv holds the district total rows printed in each profile, so "
        "the build can check that sector rows add up.",
        "Census sample records of children aged 3 to 5 (with population weights) can stand in "
        "for Table 2.5: `make intake` weights them to sector counts and marks them basis = "
        "sample, which makes their status a model estimate.",
    ),
)


def _read(directory: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    sectors = read_csv(directory / "census_2022_sectors.csv", SECTOR_COLUMNS)
    districts = read_csv(directory / "census_2022_districts.csv", DISTRICT_COLUMNS)
    return sectors, districts


def load(raw: Path = RAW) -> tuple[Loaded, Loaded]:
    """(sector rows, district total rows), each with geo_id."""
    pdfs = sorted((raw / DATASET.key / "pdf").glob("*.pdf"))
    if not DATASET.present(raw) and pdfs:
        directory, real = parse_profiles(pdfs), True
    else:
        directory, real = folder(DATASET, raw)
    sectors, districts = _read(directory)
    sectors["geo_id"] = sector_ids(DATASET.key, sectors.district_name, sectors.sector_name)
    districts["geo_id"] = district_ids(DATASET.key, districts.district_name)
    bad = (
        sectors.children_3_5_attending + sectors.children_3_5_never_attended != sectors.children_3_5
    )
    if bad.any():
        names = ", ".join(sectors.loc[bad, "sector_name"].head(5))
        raise SchemaError(f"census: attending + never attended != total for {names}")
    files = (directory / "census_2022_sectors.csv", directory / "census_2022_districts.csv")
    state = status(DATASET, real)
    if real and (sectors.basis == SAMPLE).any():
        state = MODEL
    return Loaded(sectors, state, real, files), Loaded(districts, state, real, files)
