"""Parse the 30 Census 2022 district profile PDFs into the two census CSVs.

Name each PDF after its district (Gicumbi.pdf) and put them in data/raw/census_2022/pdf/.
Table 2.5 (children aged 3 to 5 attending and never attended nursery school, by sector) is
parsed by finding the table whose header names those columns. Other tables are listed in
TABLES: add an entry once the table number and header wording are confirmed on a real profile.

Written without a real profile at hand: check the first parsed district by hand before
trusting the rest. The build's checks (sector rows add up to the district row; attending plus
never attended equals the total) catch most misreads.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pdfplumber

from irerero.config import INTERIM


@dataclass(frozen=True)
class TableSpec:
    label: str
    """Text that names the table on its page, e.g. "Table 2.5"."""
    columns: dict[str, tuple[str, ...]]
    """Output column -> words that must all appear in its header cell (lower case)."""
    exclude: dict[str, tuple[str, ...]]
    """Output column -> words that must not appear in its header cell."""


TABLES = (
    TableSpec(
        "Table 2.5",
        {
            "children_3_5": ("total",),
            "children_3_5_attending": ("attend",),
            "children_3_5_never_attended": ("never",),
        },
        {"children_3_5_attending": ("never", "not")},
    ),
)
NUMBER = re.compile(r"^-?[\d,. ]+$")


def _number(cell: str | None) -> float | None:
    if cell is None:
        return None
    text = cell.replace("\n", " ").strip()
    if not text or not NUMBER.match(text):
        return None
    return float(text.replace(",", "").replace(" ", ""))


def _header_map(header: list[str | None], spec: TableSpec) -> dict[str, int]:
    found: dict[str, int] = {}
    for column, words in spec.columns.items():
        banned = spec.exclude.get(column, ())
        for i, cell in enumerate(header):
            text = (cell or "").lower()
            if all(w in text for w in words) and not any(b in text for b in banned):
                found.setdefault(column, i)
    return found


def parse_table(pdf: Path, spec: TableSpec) -> pd.DataFrame:
    """Rows of (name, columns..., source_page) from the first table matching `spec`."""
    with pdfplumber.open(pdf) as document:
        for number, page in enumerate(document.pages, start=1):
            if spec.label.lower() not in (page.extract_text() or "").lower():
                continue
            for table in page.extract_tables():
                for h, header in enumerate(table):
                    columns = _header_map(header, spec)
                    if len(columns) < len(spec.columns):
                        continue
                    rows = []
                    for row in table[h + 1 :]:
                        name = (row[0] or "").replace("\n", " ").strip()
                        values = {c: _number(row[i]) for c, i in columns.items()}
                        if name and all(v is not None for v in values.values()):
                            rows.append({"name": name, **values, "source_page": f"p.{number}"})
                    if rows:
                        return pd.DataFrame(rows)
    raise ValueError(f"{pdf.name}: {spec.label} not found or its header did not match")


def parse_profiles(pdfs: list[Path], out: Path = INTERIM / "census_2022") -> Path:
    """Writes census_2022_sectors.csv and census_2022_districts.csv; returns their folder."""
    sectors, districts = [], []
    for pdf in pdfs:
        district = pdf.stem
        merged: pd.DataFrame | None = None
        for spec in TABLES:
            table = parse_table(pdf, spec)
            merged = (
                table if merged is None else merged.merge(table, on="name", suffixes=("", "_x"))
            )
        assert merged is not None
        is_total = merged.name.str.lower().isin(
            {"total", district.lower(), f"{district.lower()} district"}
        )
        sector_rows = merged[~is_total].rename(columns={"name": "sector_name"})
        sector_rows.insert(0, "district_name", district)
        total_rows = merged[is_total].drop(columns="name")
        total_rows.insert(0, "district_name", district)
        sectors.append(sector_rows)
        districts.append(total_rows.head(1))
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(sectors).to_csv(out / "census_2022_sectors.csv", index=False)
    pd.concat(districts).to_csv(out / "census_2022_districts.csv", index=False)
    return out
