"""Bring files received from NISR, MINEDUC and others into the data layer safely.

    python -m irerero.data.intake <file or folder> ...      (make intake FILES="...")

For each file it:

1. keeps the original, read-only, in data/raw/_received/<package>/ (gitignored, never
   redistributed) and records its name, size and SHA-256 in data/received_files.csv, the one
   committed trace of what the team holds;
2. converts it to the columns declared in irerero/data/sources/, through the reviewed
   crosswalks, without inventing or filling any value;
3. runs the quality checks below and writes them to data/interim/intake_report.md;
4. puts the converted file in data/raw/<dataset>/ only when it is complete for that dataset.
   An incomplete conversion stays in data/interim/ and the report says exactly what is
   missing, so the app keeps its labelled stand-in rather than mixing real and simulated
   values in one series.

Recognised packages: the EICV7 district poverty table (eicv7_poverty.csv with
poverty_rate_percent), the MINEDUC yearbook district tables (preprimary_*_by_district.csv)
with their national series, the census 2022 sample records of children aged 3 to 5
(sector_code, attendance_code, population_weight), the NISR single-age district projections
(.xlsx with an "All ages long" sheet; read with openpyxl, which `make intake` adds) and the
COD-AB boundary files (provinces/districts/sectors.geojson with nisr_code).

Census sample records are person-level. They stay in data/raw/_received/ only; what is staged
is the weighted count per sector, so no record reaches the build, the database or git.
"""

import argparse
import hashlib
import re
import shutil
import stat
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from irerero.config import DATA, INTERIM, RAW, REFERENCE, YEARBOOK_YEARS
from irerero.data.crosswalk import district_ids, sector_ids
from irerero.data.sources import boundaries, census, eicv, projections, yearbook
from irerero.data.sources import schools as school_source
from irerero.data.validate import SchemaError, validate

MANIFEST = DATA / "received_files.csv"
RECEIVED = RAW / "_received"
REPORT = INTERIM / "intake_report.md"
MANIFEST_COLUMNS = ("received_on", "package", "file", "bytes", "sha256", "staged_as", "note")

# Aggregate rows printed in the yearbook district tables. They are checked against the sum of
# their districts and never loaded as districts.
PROVINCE_ROWS = {"south", "west", "east", "north", "kigali city"}
NATIONAL_ROW = "rwanda"
MINEDUC_TABLES = {
    "preprimary_teaching_staff_by_district.csv": ("teachers", "total"),
    "preprimary_pupils_by_district.csv": ("pupils", "total"),
    "preprimary_teachers_by_district.csv": ("teachers", "total"),
    "preprimary_classrooms_by_district.csv": ("classrooms", "classrooms"),
    "preprimary_schools_by_district.csv": ("schools", "schools"),
}
MINEDUC_NATIONAL = (
    "ecd_and_preprimary_national_timeseries.csv",
    "participation_rate_ages_3_5.csv",
    "preprimary_staff_qualifications.csv",
    "qualified_teachers_national.csv",
)
SMALL_DIFFERENCE = 2
GAZETTEER = "rwa_gazetteer"
YEARBOOK_SOURCE = (
    "MINEDUC Education Statistical Yearbook 2024/25 (published Feb 2026), district annexes"
)
CENSUS_SAMPLE_COLUMNS = {"district_code", "sector_code", "age_years", "attendance_code",
                         "population_weight"}  # fmt: skip
ATTENDING, NEVER, UNKNOWN = 2, 3, 9  # census attendance codes for children aged 3 to 5
CENSUS_SOURCE = "PHC5 2022 sample records, children aged 3-5, weighted (IrereroAI tabulation)"
FEW_RECORDS = 100  # below this the sector's attendance rate is uncertain by about 10 points
LARGE_WEIGHT = 100
PROJECTION_SHEET = "All ages long"
PROJECTION_YEARS = tuple(range(2023, 2033))
PROJECTION_SOURCE = "NISR Subnational Population Projections 2023-2032, single-age tables"
CENSUS_MASTER_SHEET = "Sector_Census_Master"
# Table C1.2 groups the first nine sources as improved
IMPROVED_WATER = (
    "water_mineral_pct", "water_internal_piped_pct", "water_piped_compound_pct",
    "water_piped_neighbor_pct", "water_public_tap_pct", "water_borehole_pct",
    "water_protected_spring_well_pct", "water_rainwater_pct", "water_tanker_pct",
)  # fmt: skip
MASTER_COLUMNS = ("population", "households", "hh_improved_water", "hh_electricity", "urban_share")
MASTER_SOURCE = (
    "PHC5 2022 thematic reports: Table D1 (population, urban), C1.2 (drinking water), C1.5 "
    "(grid electricity, households)"
)
MINEDUC_MASTER_COLUMNS = {"district", "academic_year", "male_pupils", "female_pupils",
                          "male_teachers", "female_teachers", "schools_count",
                          "classrooms_in_use"}  # fmt: skip
BOUNDARY_FILES = ("provinces.geojson", "districts.geojson", "sectors.geojson")
BOUNDARY_COUNTS = {"provinces.geojson": 5, "districts.geojson": 30, "sectors.geojson": 416}


@dataclass(frozen=True)
class Check:
    dataset: str
    level: str
    """pass, warn or fail. A fail stops that dataset from being staged."""
    text: str


@dataclass
class Result:
    dataset: str
    checks: list[Check]
    staged: Path | None
    interim: Path | None


# --- receiving ----------------------------------------------------------------------------
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def receive(files: list[Path], package: str, raw: Path = RAW, manifest: Path = MANIFEST) -> None:
    """Keep a read-only copy of each original and record its checksum."""
    folder = raw / "_received" / package
    folder.mkdir(parents=True, exist_ok=True)
    known = (
        pd.read_csv(manifest, dtype=str)
        if manifest.exists()
        else pd.DataFrame(columns=MANIFEST_COLUMNS)
    )
    rows = []
    for path in files:
        digest = sha256(path)
        seen = {(r["file"], r["sha256"]) for r in rows}
        if ((known.file == path.name) & (known.sha256 == digest)).any() or (
            (path.name, digest) in seen
        ):
            continue
        target = folder / path.name
        if target.exists():  # a different file with the same name: keep both
            target = folder / f"{digest[:8]}-{path.name}"
        shutil.copy2(path, target)
        target.chmod(stat.S_IRUSR | stat.S_IRGRP)  # originals are never edited in place
        rows.append(
            {
                "received_on": date.today().isoformat(),
                "package": package,
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": digest,
                "staged_as": "",
                "note": "original kept in data/raw/_received/ (not in git)",
            }
        )
    if rows:
        out = pd.concat([known, pd.DataFrame(rows)], ignore_index=True)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(manifest, index=False)


def _mark_staged(manifest: Path, files: list[Path], staged_as: str) -> None:
    if not manifest.exists():
        return
    frame = pd.read_csv(manifest, dtype=str).fillna("")
    names = {p.name for p in files}
    frame.loc[frame.file.isin(names), "staged_as"] = staged_as
    frame.to_csv(manifest, index=False)


# --- EICV7 ----------------------------------------------------------------------------------
def eicv_district(path: Path) -> tuple[pd.DataFrame, list[Check]]:
    """EICV7 district headcount poverty (percent) to the eicv7_poverty.csv schema."""
    src = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    key = eicv.DATASET.key
    checks: list[Check] = []
    rate = pd.to_numeric(src.poverty_rate_percent, errors="coerce")
    if rate.isna().any() or ((rate < 0) | (rate > 100)).any():
        checks.append(Check(key, "fail", "poverty_rate_percent must be a number from 0 to 100"))
    if "year" in src and set(src.year) != {"2023/24"}:
        checks.append(Check(key, "fail", f"year must be 2023/24, got {sorted(set(src.year))}"))
    if "geographic_level" in src and set(src.geographic_level.str.lower()) != {"district"}:
        levels = sorted(set(src.geographic_level))
        checks.append(Check(key, "fail", f"expected district rows only, got {levels}"))
    out = pd.DataFrame(
        {
            "level": "district",
            "district_name": src.district.str.strip(),
            "sector_name": "",
            "poverty_rate": (rate / 100).round(4),
            "source_page": src.get("source", pd.Series("EICV7", index=src.index)),
        }
    )
    try:
        ids = district_ids(key, out.district_name)
        n = ids.nunique()
        level = "pass" if n == 30 and not ids.duplicated().any() else "fail"
        checks.append(Check(key, level, f"{n} of 30 districts, each once, joined to the crosswalk"))
    except SchemaError as error:
        checks.append(Check(key, "fail", str(error)))
    try:
        validate(out, eicv.DATASET.columns, path.name)
    except SchemaError as error:
        checks.append(Check(key, "fail", str(error)))
    ties = out[out.poverty_rate.duplicated(keep=False)].sort_values("poverty_rate")
    if len(ties):
        pairs = "; ".join(
            f"{', '.join(g.district_name)} at {v:.1%}" for v, g in ties.groupby("poverty_rate")
        )
        checks.append(
            Check(key, "warn", f"identical values to re-check against the chart: {pairs}")
        )
    notes = set(src.get("source_note", pd.Series(dtype=str)).dropna())
    for note in sorted(notes):
        checks.append(Check(key, "warn", f"source note: {note}"))
    checks.append(
        Check(
            key,
            "warn",
            "district level only: every sector takes its district's rate (labelled 'district'), "
            "so poverty no longer separates sectors inside a district in the priority index",
        )
    )
    return out, checks


# --- MINEDUC ------------------------------------------------------------------------------
def _year(token: str) -> str:
    """'2023_24' -> '2023/24'."""
    return token.replace("_", "/")


def _split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    name = frame.columns[0]
    lowered = frame[name].str.strip().str.casefold()
    aggregate = lowered.isin(PROVINCE_ROWS | {NATIONAL_ROW})
    return frame[~aggregate], frame[aggregate]


def mineduc_district(paths: list[Path]) -> tuple[pd.DataFrame, list[Check]]:
    """Yearbook district tables to the long yearbook schema, aggregates checked and dropped."""
    key = yearbook.DATASET.key
    checks: list[Check] = []
    long = []
    for path in paths:
        measure, prefix = MINEDUC_TABLES[path.name]
        frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        name = frame.columns[0]
        frame[name] = frame[name].str.strip()
        districts, aggregates = _split(frame)
        year_cols = [c for c in frame.columns if re.fullmatch(rf"{prefix}_\d{{4}}_\d{{2}}", c)]
        for col in year_cols:
            period = col.removeprefix(f"{prefix}_")
            parts = [c for c in frame.columns if c != col and c.endswith(f"_{period}")]
            if len(parts) != 2:
                continue
            nums = frame[[col, *parts]].apply(lambda c: pd.to_numeric(c.str.replace(",", "")))
            off = frame[nums[parts].sum(axis=1) != nums[col]]
            for i in off.index:
                total, both = int(nums.at[i, col]), int(nums.loc[i, parts].sum())
                # a point or two is common in printed tables; more is a transcription error
                level = "warn" if abs(both - total) <= SMALL_DIFFERENCE else "fail"
                checks.append(
                    Check(key, level, f"{path.name} {frame.at[i, name]} {_year(period)}: "
                          f"{' + '.join(parts)} = {both:,}, but {col} = {total:,}; "
                          "check the source table")
                )  # fmt: skip
        for col in year_cols:
            values = pd.to_numeric(frame[col].str.replace(",", ""), errors="coerce")
            dist = values[districts.index]
            nat = values[aggregates.index[aggregates[name].str.casefold() == NATIONAL_ROW]]
            if dist.isna().any():
                checks.append(Check(key, "fail", f"{path.name} {col}: blank or non-numeric cells"))
            if len(nat) and int(dist.sum()) != int(nat.iat[0]):
                checks.append(
                    Check(key, "fail", f"{path.name} {col}: districts add to {int(dist.sum()):,}"
                          f", the Rwanda row says {int(nat.iat[0]):,}")
                )  # fmt: skip
            # each province row equals the districts printed above it
            start = 0
            for i in aggregates.index:
                if frame.at[i, name].casefold() == NATIONAL_ROW:
                    continue
                block = values[[j for j in districts.index if start <= j < i]]
                if int(block.sum()) != int(values[i]):
                    checks.append(
                        Check(key, "fail", f"{path.name} {col}: {frame.at[i, name]} row "
                              f"{int(values[i]):,} vs districts {int(block.sum()):,}")
                    )  # fmt: skip
                start = i + 1
            long.append(
                pd.DataFrame(
                    {
                        "district_name": districts[name].to_numpy(),
                        "school_year": _year(col.removeprefix(f"{prefix}_")),
                        "measure": measure,
                        "value": dist.to_numpy(),
                    }
                )
            )
        checks.append(
            Check(key, "pass", f"{path.name}: {len(districts)} districts, years "
                  f"{', '.join(_year(c.removeprefix(prefix + '_')) for c in year_cols)}; "
                  "province and national rows match their districts unless listed above")
        )  # fmt: skip
    if not long:
        return pd.DataFrame(), checks
    tidy = pd.concat(long, ignore_index=True)
    # Yearbooks repeat earlier years: identical repeats are fine, different values are not.
    cell = ["district_name", "school_year", "measure"]
    tidy = tidy.drop_duplicates()
    clash = tidy[tidy.duplicated(cell, keep=False)]
    for (d, y, m), rows in clash.groupby(cell):
        values = ", ".join(f"{v:,.0f}" for v in rows.value)
        checks.append(Check(key, "fail", f"{d} {y} {m}: two files disagree ({values})"))
    tidy = tidy.drop_duplicates(cell)
    wide = (
        tidy.pivot_table(
            index=["district_name", "school_year"], columns="measure", values="value",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(columns=None)
    )  # fmt: skip
    district_ids(key, wide.district_name)  # every name must be in the crosswalk
    for col in ("pupils", "schools", "classrooms", "teachers", "qualified_teachers"):
        wide[col] = (wide[col] if col in wide else pd.Series(pd.NA, index=wide.index)).astype(
            "Int64"
        )
    wide["source_page"] = YEARBOOK_SOURCE
    wide = wide[["district_name", "school_year", "pupils", "schools", "classrooms", "teachers",
                 "qualified_teachers", "source_page"]]  # fmt: skip
    return wide.sort_values(["district_name", "school_year"]).reset_index(drop=True), checks


def yearbook_gaps(wide: pd.DataFrame) -> list[str]:
    """What stops the table from standing in for all 30 districts and every yearbook year."""
    gaps = []
    required = [c.name for c in yearbook.DATASET.columns if c.required and c.name != "school_year"]
    districts = wide.district_name.nunique() if len(wide) else 0
    if districts != 30:
        gaps.append(f"{districts} of 30 districts")
    for year in YEARBOOK_YEARS:
        rows = wide[wide.school_year == year]
        if rows.empty:
            gaps.append(f"{year}: no district table")
            continue
        missing = [c for c in required if c != "district_name" and rows[c].isna().any()]
        if missing:
            gaps.append(f"{year}: {', '.join(missing)} missing")
    return gaps


def mineduc_national(paths: list[Path]) -> tuple[pd.DataFrame, list[Check]]:
    """The national series, tidied for reference. They are not loaded into the pipeline: the
    app's trend is built from district rows, and these use other definitions."""
    key = yearbook.DATASET.key
    checks: list[Check] = []
    frames = []
    for path in paths:
        frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        period = "academic_year" if "academic_year" in frame else "year"
        value = next(c for c in frame.columns if c not in ("indicator", period))
        frames.append(
            pd.DataFrame(
                {
                    "file": path.name,
                    "indicator": frame.indicator,
                    "period": frame[period].map(_year),
                    "period_type": "school year" if period == "academic_year" else "calendar year",
                    "value": pd.to_numeric(frame[value], errors="coerce"),
                    "unit": "percent" if value.endswith("percent") else "count",
                }
            )
        )
    if not frames:
        return pd.DataFrame(), checks
    out = pd.concat(frames, ignore_index=True)
    series = out.set_index(["indicator", "period"]).value
    centres = series.get("total_children_in_ecd_centres")
    if centres is not None and {"2020/21", "2021/22"} <= set(centres.index):
        ratio = centres["2021/22"] / centres["2020/21"]
        if ratio > 2:
            checks.append(
                Check(key, "warn", f"children in ECD centres rise {ratio:.1f}x from 2020/21 to "
                      "2021/22: a break in coverage, not growth; do not trend across it")
            )  # fmt: skip
    if out.value.isna().any():
        blank = out[out.value.isna()][["indicator", "period"]].astype(str).agg(" ".join, axis=1)
        checks.append(Check(key, "warn", f"blank in the source: {', '.join(blank)}"))
    checks.append(
        Check(key, "warn", "participation_rate_ages_3_5 is a calendar-year MINEDUC rate; the app "
              "uses a gross rate (pupils per child aged 3-5). They are shown apart, never mixed")
    )  # fmt: skip
    return out, checks


def cross_checks(wide: pd.DataFrame, national: pd.DataFrame) -> list[Check]:
    key = yearbook.DATASET.key
    checks = []
    if wide.empty or national.empty:
        return checks
    series = national.set_index(["indicator", "period"]).value
    for measure, indicator in (("pupils", "total_preprimary_pupils"),
                               ("teachers", "total_preprimary_staff")):  # fmt: skip
        for year, total in wide.groupby("school_year")[measure].sum(min_count=1).dropna().items():
            if (indicator, year) not in series.index:
                continue
            nat = series[(indicator, year)]
            gap = int(total) - int(nat)
            level = "pass" if gap == 0 else "warn"
            checks.append(
                Check(key, level, f"{measure} {year}: districts {int(total):,} vs national "
                      f"{indicator} {int(nat):,}" + (f" (difference {gap:+,})" if gap else ""))
            )  # fmt: skip
    share = national[national.indicator == "qualified_staff_percent"]
    if len(share):
        checks.append(
            Check(key, "warn", f"qualified staff {share.value.iloc[-1]:.1f}% nationally, and "
                  "only nationally: qualified_teachers by district is still needed")
        )  # fmt: skip
    return checks


# --- crosswalk names ------------------------------------------------------------------------
def _official_names() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(sectors, districts) by NISR code, with the names the crosswalk joins on."""
    sectors = pd.read_csv(REFERENCE / "sector_name_crosswalk.csv", dtype=str).fillna("")
    sectors = sectors[(sectors.source == "*") & (sectors.nisr_sector_code != "")]
    districts = pd.read_csv(REFERENCE / "district_name_crosswalk.csv", dtype=str).fillna("")
    districts = districts[(districts.source == "*") & (districts.nisr_district_code != "")]
    return (
        sectors.set_index("nisr_sector_code")[["geo_id", "source_district", "source_sector"]],
        districts.set_index("nisr_district_code")[["geo_id", "source_district"]],
    )


# --- Census 2022 sample records -------------------------------------------------------------
def census_sample(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[Check]]:
    """Weighted counts of children aged 3 to 5 attending and never attended, per sector, from
    census sample records (one row per child with a population weight)."""
    key = census.DATASET.key
    checks: list[Check] = []
    src = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    missing = CENSUS_SAMPLE_COLUMNS - set(src.columns)
    if missing:
        checks.append(Check(key, "fail", f"{path.name}: missing column(s) {sorted(missing)}"))
        return pd.DataFrame(), pd.DataFrame(), checks
    codes = ["district_code", "sector_code", "age_years", "attendance_code"]
    numbers = src[[*codes, "population_weight"]].apply(pd.to_numeric, errors="coerce")
    if numbers.isna().any().any():
        bad = numbers.columns[numbers.isna().any()].tolist()
        checks.append(Check(key, "fail", f"blank or non-numeric values in {bad}"))
        return pd.DataFrame(), pd.DataFrame(), checks
    src[numbers.columns] = numbers
    src[codes] = src[codes].astype(int)
    weight = src.population_weight
    checks.append(
        Check(key, "pass", f"{len(src):,} sample records of children, weighted to "
              f"{weight.sum():,.0f} children aged 3 to 5 (weights {weight.min():.1f} to "
              f"{weight.max():.1f}, median {weight.median():.1f})")
    )  # fmt: skip
    ages = sorted(set(src.age_years))
    if ages != [3, 4, 5]:
        checks.append(Check(key, "fail", f"age_years must be 3, 4 and 5, got {ages}"))
    if (weight <= 0).any():
        checks.append(Check(key, "fail", "population_weight must be positive"))
    other = sorted(set(src.attendance_code) - {ATTENDING, NEVER, UNKNOWN})
    if other:
        checks.append(Check(key, "fail", f"unexpected attendance codes {other}"))
    if "attendance_status" in src:
        labels = src.groupby("attendance_code").attendance_status.agg(lambda v: sorted(set(v)))
        checks.append(
            Check(key, "pass", "attendance codes: " + "; ".join(
                f"{c} = {', '.join(map(str, v))}" for c, v in labels.items()))
        )  # fmt: skip
    nested = src.sector_code // 100 == src.district_code
    if not nested.all():
        checks.append(
            Check(key, "fail", f"{(~nested).sum()} records whose sector code is not inside "
                  "their district code")
        )  # fmt: skip
    unknown = src.attendance_code == UNKNOWN
    if unknown.any():
        checks.append(
            Check(key, "warn", f"{unknown.sum()} record(s), {weight[unknown].sum():.0f} weighted "
                  "children, with attendance not stated: left out of the sector counts")
        )  # fmt: skip
    heavy = src[weight > LARGE_WEIGHT]
    if len(heavy):
        where = ", ".join(sorted(set(heavy.district + " / " + heavy.sector)))
        checks.append(
            Check(key, "warn", f"{len(heavy)} records carry weights above {LARGE_WEIGHT} (up to "
                  f"{heavy.population_weight.max():.0f}), in {where}: these sectors' counts lean "
                  "on few households")
        )  # fmt: skip

    sectors, _ = _official_names()
    src["nisr_code"] = "RW" + src.sector_code.astype(str)
    stated = src[~unknown]
    per = stated.pivot_table(
        index="nisr_code", columns="attendance_code", values="population_weight",
        aggfunc="sum", fill_value=0.0,
    )  # fmt: skip
    records = src.groupby("nisr_code").size()
    unmatched = sorted(set(per.index) - set(sectors.index))
    if unmatched:
        checks.append(
            Check(key, "fail", f"{len(unmatched)} sector code(s) not in the reviewed crosswalk: "
                  f"{', '.join(unmatched[:10])}")
        )  # fmt: skip
        return pd.DataFrame(), pd.DataFrame(), checks
    names = sectors.loc[per.index]
    printed = src.drop_duplicates("nisr_code").set_index("nisr_code").loc[per.index]
    if "sector" in printed:
        differ = names[
            printed.sector.str.strip().str.casefold() != names.source_sector.str.casefold()
        ]
        for code, row in differ.iterrows():
            checks.append(
                Check(key, "warn", f"{code}: the census spells the sector "
                      f"'{printed.at[code, 'sector']}', the crosswalk '{row.source_sector}'; "
                      "joined by code")
            )  # fmt: skip
    attending = per.get(ATTENDING, 0.0).round().astype(int)
    never = per.get(NEVER, 0.0).round().astype(int)
    out = pd.DataFrame(
        {
            "sector_name": names.source_sector,
            "district_name": names.source_district,
            "children_3_5": attending + never,
            "children_3_5_attending": attending,
            "children_3_5_never_attended": never,
            "basis": census.SAMPLE,
            "source_page": CENSUS_SOURCE,
        }
    )
    n_sectors, n_districts = len(out), out.district_name.nunique()
    level = "pass" if (n_sectors, n_districts) == (416, 30) else "fail"
    checks.append(
        Check(key, level, f"{n_sectors} of 416 sectors and {n_districts} of 30 districts, each "
              "once, joined to the crosswalk by NISR code")
    )  # fmt: skip
    few = records[records < FEW_RECORDS]
    if len(few):
        rate = (attending / out.children_3_5).loc[few.index]
        margin = (1.96 * (rate * (1 - rate) / few) ** 0.5).max()
        checks.append(
            Check(key, "warn", f"{len(few)} sectors rest on fewer than {FEW_RECORDS} sampled "
                  f"children (fewest {few.min()}): their attendance rates are uncertain by up to "
                  f"about ±{margin:.0%} (simple random sample approximation)")
        )  # fmt: skip
    rate = attending.sum() / out.children_3_5.sum()
    checks.append(
        Check(key, "pass", f"{rate:.1%} of children aged 3 to 5 attending nationally "
              f"({attending.sum():,} of {out.children_3_5.sum():,})")
    )  # fmt: skip
    totals = (
        out.groupby("district_name")[
            ["children_3_5", "children_3_5_attending", "children_3_5_never_attended"]
        ]
        .sum()
        .reset_index()
        .assign(source_page=CENSUS_SOURCE + ", sum of its sectors")
    )
    checks.append(
        Check(key, "warn", "district totals are the sums of their sectors, so the build's "
              "'sectors add up' check cannot catch an error here; compare them with the printed "
              "Table 2.5 district totals when the profiles are in hand")
    )  # fmt: skip
    checks.append(
        Check(key, "warn", "Table 2.5 counts only: population, children 0-4, households, water, "
              "sanitation, electricity, urban share and women's education are not in this file, "
              "so the home-environment factor and those peer-model features stay empty")
    )  # fmt: skip
    for frame, columns, name in (
        (out, census.SECTOR_COLUMNS, "census_2022_sectors.csv"),
        (totals, census.DISTRICT_COLUMNS, "census_2022_districts.csv"),
    ):
        try:
            validate(frame.reset_index(drop=True), columns, name)
        except SchemaError as error:
            checks.append(Check(key, "fail", str(error)))
    return out.sort_values(["district_name", "sector_name"]).reset_index(drop=True), totals, checks


# --- Census 2022 sector tables (the master workbook) ----------------------------------------
def census_master(path: Path) -> tuple[pd.DataFrame, list[Check]]:
    """Population, urban share, households, improved water and grid electricity per sector,
    from the census thematic-report tables merged in the master workbook."""
    try:
        sheets = pd.read_excel(path, sheet_name=None)
    except ImportError:
        key = census.DATASET.key
        return pd.DataFrame(), [Check(key, "fail", "reading .xlsx needs openpyxl: `make intake`")]
    return census_master_from_sheets(sheets)


def census_master_from_sheets(sheets: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, list[Check]]:
    key = census.DATASET.key
    checks: list[Check] = []
    m = sheets[CENSUS_MASTER_SHEET]
    need = {"district", "sector", "population_total", "households_total_count",
            "water_households_total_count", "grid_connected_households_count",
            *IMPROVED_WATER}  # fmt: skip
    if need - set(m.columns):
        checks.append(Check(key, "fail", f"missing column(s) {sorted(need - set(m.columns))}"))
        return pd.DataFrame(), checks
    try:
        ids = sector_ids(key, m.district, m.sector)
    except SchemaError as error:
        checks.append(Check(key, "fail", str(error)))
        return pd.DataFrame(), checks
    n = ids.nunique()
    checks.append(
        Check(key, "pass" if n == 416 and not ids.duplicated().any() else "fail",
              f"{n} of 416 sectors, each once, joined to the crosswalk by name")
    )  # fmt: skip
    population = pd.to_numeric(m.population_total, errors="coerce")
    if population.isna().any() or (population <= 0).any():
        checks.append(Check(key, "fail", "population missing or not positive in some sectors"))
    published = sheets.get("District_Validation")
    if published is not None:
        rwanda = published[published.iloc[:, 0].astype(str).str.upper() == "RWANDA"]
        if len(rwanda):
            total = int(rwanda.iloc[0, 1])
            gap = int(population.sum()) - total
            checks.append(
                Check(key, "pass" if gap == 0 else "warn", f"sector populations add to "
                      f"{int(population.sum()):,}; the published national total (Table 3.10) is "
                      f"{total:,}" + (f" (difference {gap:+,})" if gap else ""))
            )  # fmt: skip
    urban = pd.to_numeric(m.get("urban_population_total"), errors="coerce").fillna(0)
    rural = pd.to_numeric(m.get("rural_population_total"), errors="coerce").fillna(0)
    off = (urban + rural != population).sum()
    checks.append(
        Check(key, "pass" if off == 0 else "warn", f"urban + rural = population in all but {off} "
              "sectors (a blank urban or rural cell is read as 0)")
    )  # fmt: skip
    households = pd.to_numeric(m.households_total_count, errors="coerce")
    water_households = pd.to_numeric(m.water_households_total_count, errors="coerce")
    differ = int((households != water_households).sum())
    if differ:
        checks.append(
            Check(key, "warn", f"{differ} sectors: the water table's household count differs from "
                  "the household total; improved water uses the water table's own count")
        )  # fmt: skip
    shares = m[[c for c in m.columns if c.startswith("water_") and c.endswith("_pct")]]
    off = int((shares.sum(axis=1) - 1).abs().gt(0.01).sum())
    checks.append(
        Check(key, "pass" if off == 0 else "warn", f"drinking-water shares add to 100% (±1 point) "
              f"in all but {off} sectors")
    )  # fmt: skip
    improved = m[list(IMPROVED_WATER)].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    grid = pd.to_numeric(m.grid_connected_households_count, errors="coerce")
    over = int((grid > households).sum())
    if over:
        checks.append(Check(key, "fail", f"{over} sectors with more grid-connected households "
                            "than households"))  # fmt: skip
    names = _official_names()[0].reset_index().set_index("geo_id")
    out = pd.DataFrame(
        {
            "sector_name": ids.map(names.source_sector).to_numpy(),
            "district_name": ids.map(names.source_district).to_numpy(),
            "population": population.round().astype("Int64").to_numpy(),
            "households": households.round().astype("Int64").to_numpy(),
            "hh_improved_water": (improved * water_households).round().astype("Int64").to_numpy(),
            "hh_electricity": grid.round().astype("Int64").to_numpy(),
            "urban_share": (urban / population).round(4).to_numpy(),
        }
    )
    checks.append(
        Check(key, "pass", f"{(out.urban_share > 0).sum()} sectors with an urban population; "
              f"improved drinking water {out.hh_improved_water.sum() / out.households.sum():.1%}"
              f" and grid electricity {out.hh_electricity.sum() / out.households.sum():.1%} of "
              "households nationally")
    )  # fmt: skip
    checks.append(
        Check(key, "warn", "not at sector level in the source, so left empty: improved "
              "sanitation (Table 8.3 is by province), women's education (Education thematic "
              "report needed) and children aged 0 to 4 (Table C4 is national)")
    )  # fmt: skip
    return out, checks


def merge_census(counts: pd.DataFrame, extra: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The sample's attendance counts with the master's sector columns; (sectors, districts)."""
    keys = ["district_name", "sector_name"]
    base = counts.drop(columns=[c for c in MASTER_COLUMNS if c in counts])
    merged = base.merge(extra, on=keys, how="left", validate="one_to_one")
    pages = merged.source_page.fillna("").astype(str)
    merged["source_page"] = pages.where(
        pages.str.contains("Table D1"), pages + "; " + MASTER_SOURCE
    )
    sums = ["children_3_5", "children_3_5_attending", "children_3_5_never_attended",
            "population", "households", "hh_improved_water", "hh_electricity"]  # fmt: skip
    numbers = merged[sums].apply(pd.to_numeric, errors="coerce")
    districts = numbers.groupby(merged.district_name).sum(min_count=1).round().astype("Int64")
    districts = districts.reset_index().assign(source_page="sum of its sectors")
    return merged, districts


def mineduc_master(path: Path) -> tuple[pd.DataFrame, list[Check]]:
    """The district-year master table (all five yearbooks) to the yearbook schema. Totals are
    boys + girls and men + women; printed totals that differ are listed, not used."""
    key = yearbook.DATASET.key
    checks: list[Check] = []
    m = pd.read_csv(path, encoding="utf-8-sig")
    m["district"] = m.district.astype(str).str.strip()
    years = tuple(sorted(m.academic_year.unique()))
    if years != YEARBOOK_YEARS:
        checks.append(Check(key, "fail", f"school years must be {YEARBOOK_YEARS}, got {years}"))
    if m.duplicated(["district", "academic_year"]).any():
        checks.append(Check(key, "fail", "a district-year appears twice"))
    numbers = ["schools_count", "classrooms_in_use", "male_pupils", "female_pupils",
               "male_teachers", "female_teachers"]  # fmt: skip
    values = m[numbers].apply(pd.to_numeric, errors="coerce")
    if values.isna().any().any() or (values < 0).any().any():
        bad = values.columns[values.isna().any() | (values < 0).any()].tolist()
        checks.append(Check(key, "fail", f"blank, non-numeric or negative cells in {bad}"))
        return pd.DataFrame(), checks
    pupils = values.male_pupils + values.female_pupils
    teachers = values.male_teachers + values.female_teachers
    corrected = set()  # (district, school year, measure) where the printed total is not used
    for label, total, column in (("pupils", pupils, "pupils_reported_total"),
                                 ("teachers", teachers, "teachers_reported_total")):  # fmt: skip
        if column not in m:
            continue
        printed = pd.to_numeric(m[column], errors="coerce")
        off = m[printed != total]
        corrected |= {(r.district, r.academic_year, label) for r in off.itertuples()}
        if len(off):
            listed = "; ".join(
                f"{r.district} {r.academic_year} {int(printed[i]):,} vs {int(total[i]):,}"
                for i, r in off.iterrows()
            )
            checks.append(
                Check(key, "warn", f"{label}: printed total differs from the sum by sex in "
                      f"{len(off)} rows, the sum is used: {listed}")
            )  # fmt: skip
    try:
        ids = district_ids(key, m.district)
    except SchemaError as error:
        checks.append(Check(key, "fail", str(error)))
        return pd.DataFrame(), checks
    sources = [c for c in m.columns if c.startswith("source_")]
    page = m[sources].fillna("").astype(str).agg(
        lambda r: "; ".join(dict.fromkeys(v for v in r if v)), axis=1
    ) if sources else pd.Series(YEARBOOK_SOURCE, index=m.index)  # fmt: skip
    _, names = _official_names()
    names = names.reset_index().set_index("geo_id").source_district
    qualified = pd.to_numeric(m.get("qualified_teachers_district"), errors="coerce")
    wide = pd.DataFrame(
        {
            "district_name": ids.map(names).to_numpy(),
            "school_year": m.academic_year.to_numpy(),
            "pupils": pupils.astype("Int64").to_numpy(),
            "schools": values.schools_count.astype("Int64").to_numpy(),
            "classrooms": values.classrooms_in_use.astype("Int64").to_numpy(),
            "teachers": teachers.astype("Int64").to_numpy(),
            "qualified_teachers": qualified.round().astype("Int64").to_numpy(),
            "source_page": (
                "MINEDUC Education Statistical Yearbook, district annex: " + page
            ).to_numpy(),
        }
    )
    n = wide.district_name.nunique()
    checks.append(
        Check(key, "pass" if n == 30 else "fail", f"{n} of 30 districts joined to the crosswalk, "
              f"{len(years)} school years each")
    )  # fmt: skip
    if wide.qualified_teachers.isna().all():
        checks.append(
            Check(key, "warn", "qualified teachers are not published by district (99.4% "
                  "nationally in 2024/25): the capacity factor uses the pupil-teacher and "
                  "pupil-classroom ratios only")
        )  # fmt: skip
    wide = wide.sort_values(["district_name", "school_year"]).reset_index(drop=True)
    wide.attrs["corrected"] = corrected
    return wide, checks


def corroborate(wide: pd.DataFrame, others: pd.DataFrame, label: str) -> Check:
    """Every cell two yearbook tables share must agree, except where `wide` uses the sum by sex
    instead of a printed total that differs (those are listed in its own check)."""
    key = yearbook.DATASET.key
    cell = ["district_name", "school_year"]
    joined = wide.merge(others, on=cell, suffixes=("", "_other"))
    differ = []
    for column in ("pupils", "schools", "classrooms", "teachers"):
        other = f"{column}_other"
        if other in joined:
            both = joined[joined[column].notna() & joined[other].notna()]
            differ += [f"{r.district_name} {r.school_year} {column}" for r in
                       both[both[column] != both[other]].itertuples()
                       if (r.district_name, r.school_year, column)
                       not in wide.attrs.get("corrected", set())]  # fmt: skip
    if differ:
        return Check(
            key, "fail", f"{label} disagrees in {len(differ)} cells: {', '.join(differ[:8])}"
        )
    known = len(wide.attrs.get("corrected", ()))
    return Check(key, "pass", f"agrees with {label} in all {len(joined)} shared district-years"
                 + (f", apart from the {known} printed totals replaced by the sum by sex" if known
                    else ""))  # fmt: skip


def mineduc_long(paths: list[Path]) -> pd.DataFrame:
    """The validated long tables (district, academic_year, ...) in the yearbook columns."""
    measures = {
        "preprimary_pupils_by_district.csv": ("pupils", "total"),
        "preprimary_teaching_staff_by_district.csv": ("teachers", "total"),
        "preprimary_classrooms_by_district.csv": ("classrooms", "classrooms_in_use"),
        "preprimary_schools_by_district.csv": ("schools", "preprimary_school_count"),
    }
    frames = []
    for path in paths:
        measure, column = measures[path.name]
        frame = pd.read_csv(path, encoding="utf-8-sig")
        frames.append(
            pd.DataFrame(
                {"district_name": frame.district.str.strip(), "school_year": frame.academic_year,
                 measure: pd.to_numeric(frame[column], errors="coerce")}
            ).set_index(["district_name", "school_year"])
        )  # fmt: skip
    return pd.concat(frames, axis=1).reset_index() if frames else pd.DataFrame()


def school_points(path: Path) -> list[Check]:
    """School locations for the distance layer, read by the same loader the app uses. A list
    of standalone pre-primary schools only is staged as provisional: shown and labelled, its
    distances an upper bound, never proof that an area has no school nearby."""
    key = school_source.DATASET.key
    frame, report = school_source.read(path)
    checks = [Check(key, "fail", error) for error in report.errors]
    if report.loaded == 0:
        return [*checks, Check(key, "fail", "no record with a usable point")]
    pupils = frame.preprimary_students_total.sum()
    missing = {k: v for k, v in report.missing_properties.items() if v}
    checks += [
        Check(key, "pass", f"{report.loaded} of {report.features} records loaded; categories "
              f"{report.categories}; {frame.district.nunique()} districts; {pupils:,} pre-primary "
              "pupils"),
        Check(key, "pass" if not report.invalid_coordinates else "warn",
              f"{report.invalid_coordinates} records with coordinates outside Rwanda or not "
              f"numbers, {report.missing_geometry} without a point: left out, never guessed"),
        Check(key, "warn" if missing else "pass", f"missing properties: {missing or 'none'}"),
        Check(key, "warn" if report.duplicate_points else "pass",
              f"{report.duplicate_points} points repeat another school's coordinates (kept: "
              "two schools can share a site)"),
        Check(key, "warn", "provisional: only standalone pre-primary schools are listed. MINEDUC "
              "counts 4,221 schools with pre-primary (2024/25), most of them primary schools "
              "with a pre-primary section. Distances from this list are an upper bound and are "
              "not used as evidence in the bottleneck rules. Still needed: the full register"),
    ]  # fmt: skip
    return checks


# --- NISR projections -----------------------------------------------------------------------
def projections_single_age(path: Path) -> tuple[pd.DataFrame, list[Check]]:
    """Single-age district projections to population and children aged 3 to 5 per year."""
    try:
        sheets = pd.read_excel(path, sheet_name=None)
    except ImportError:
        key = projections.DATASET.key
        return pd.DataFrame(), [Check(key, "fail", "reading .xlsx needs openpyxl: `make intake`")]
    return projections_from_sheets(sheets)


def projections_from_sheets(sheets: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, list[Check]]:
    key = projections.DATASET.key
    checks: list[Check] = []
    src = sheets[PROJECTION_SHEET].copy()
    need = {"district", "year", "age", "sex", "population"}
    if need - set(src.columns):
        checks.append(Check(key, "fail", f"missing column(s) {sorted(need - set(src.columns))}"))
        return pd.DataFrame(), checks
    src["age"] = src.age.astype(str).str.strip()
    src["population"] = pd.to_numeric(src.population, errors="coerce")
    if src.population.isna().any() or (src.population < 0).any():
        checks.append(Check(key, "fail", "blank, non-numeric or negative population cells"))
        return pd.DataFrame(), checks
    cell = ["district", "year", "age", "sex"]
    if src.duplicated(cell).any():
        checks.append(Check(key, "fail", f"{src.duplicated(cell).sum()} repeated cells"))
    years = tuple(sorted(src.year.unique()))
    if years != PROJECTION_YEARS:
        checks.append(Check(key, "fail", f"years must be 2023 to 2032, got {years}"))
    wide = src.pivot_table(index=cell[:3], columns="sex", values="population", aggfunc="sum")
    if {"Both sexes", "Female", "Male"} <= set(wide.columns):
        off = wide[wide.Female + wide.Male != wide["Both sexes"]]
        level = "pass" if off.empty else "fail"
        checks.append(Check(key, level, f"female + male = both sexes in all but {len(off)} cells"))
    both = src[src.sex == "Both sexes"]
    population = both.groupby(["district", "year"]).population.sum()
    printed = sheets.get("District totals")
    if printed is not None:
        printed = printed[printed.sex == "Both sexes"].set_index(["district", "year"]).population
        gap = (population - printed.reindex(population.index)).abs()
        level = "pass" if (gap.fillna(1) == 0).all() else "fail"
        checks.append(
            Check(key, level, "single ages add up to the printed district totals"
                  + ("" if level == "pass" else f" except {int((gap != 0).sum())} district-years"))
        )  # fmt: skip
    children = both[both.age.isin(["3", "4", "5"])].groupby(["district", "year"]).population.sum()
    out = pd.DataFrame({"population": population, "children_3_5": children}).reset_index()
    try:
        ids = district_ids(key, out.district)
    except SchemaError as error:
        checks.append(Check(key, "fail", str(error)))
        return pd.DataFrame(), checks
    _, districts = _official_names()
    names = districts.reset_index().set_index("geo_id").source_district
    out["district_name"] = ids.map(names).to_numpy()
    n = out.district_name.nunique()
    checks.append(
        Check(key, "pass" if n == 30 else "fail", f"{n} of 30 districts joined to the crosswalk, "
              f"{len(years)} years each")
    )  # fmt: skip
    files = sheets.get("Duplicate check")
    if files is not None and "identical_content" in files:
        repeated = files[files.uploads > 1]
        same = bool(files.identical_content.all())
        if len(repeated):
            checks.append(
                Check(key, "pass" if same else "fail", f"{len(repeated)} districts were supplied "
                      "more than once; " + ("the copies are identical" if same else
                                            "the copies differ"))
            )  # fmt: skip
    national = out.groupby("year")[["population", "children_3_5"]].sum()
    checks.append(
        Check(key, "pass", f"Rwanda {national.population.iat[0]:,} in {years[0]} to "
              f"{national.population.iat[-1]:,} in {years[-1]}; children aged 3 to 5 "
              f"{national.children_3_5.iat[0]:,} to {national.children_3_5.iat[-1]:,}")
    )  # fmt: skip
    checks.append(
        Check(key, "warn", "one projection only (the variant is not stated; read as the main, "
              "medium variant): the 2026 estimate's range uses the default ±"
              "projection error instead of low and high variants")
    )  # fmt: skip
    if "source_file" in src:
        source = src.groupby("district").source_file.first()
        out["source_page"] = PROJECTION_SOURCE + " (" + out.district.map(source) + ")"
    else:
        out["source_page"] = PROJECTION_SOURCE
    out = out[["district_name", "year", "population", "children_3_5", "source_page"]]
    try:
        validate(out, projections.DATASET.columns, projections.FILE)
    except SchemaError as error:
        checks.append(Check(key, "fail", str(error)))
    return out.sort_values(["district_name", "year"]).reset_index(drop=True), checks


# --- boundaries -----------------------------------------------------------------------------
def boundary_files(paths: list[Path]) -> tuple[dict[str, object], list[Check]]:
    """COD-AB GeoJSON, checked and slimmed to nisr_code, name, parent_nisr_code and shape."""
    import geopandas as gpd

    key = boundaries.DATASET.key
    checks: list[Check] = []
    by_name = {p.name: p for p in paths}
    missing = [f for f in BOUNDARY_FILES if f not in by_name]
    if missing:
        checks.append(Check(key, "fail", f"missing {', '.join(missing)}"))
        return {}, checks
    sectors, districts = _official_names()
    frames = {}
    for name in BOUNDARY_FILES:
        frame = gpd.read_file(by_name[name])
        need = {"nisr_code", "name", "parent_nisr_code"}
        if need - set(frame.columns):
            checks.append(
                Check(key, "fail", f"{name}: missing {sorted(need - set(frame.columns))}")
            )
            continue
        epsg = frame.crs.to_epsg() if frame.crs else None
        if epsg != 4326:
            checks.append(Check(key, "warn", f"{name}: CRS {frame.crs}, reprojected to EPSG:4326"))
            frame = frame.to_crs(4326)
        frame = frame[["nisr_code", "name", "parent_nisr_code", "geometry"]].copy()
        empty = frame.geometry.isna() | frame.geometry.is_empty
        invalid = ~frame.geometry.is_valid & ~empty
        if invalid.any():
            frame.loc[invalid, "geometry"] = frame.loc[invalid].geometry.make_valid()
            checks.append(
                Check(key, "warn", f"{name}: {int(invalid.sum())} invalid shape(s) repaired "
                      "with make_valid (self-intersections)")
            )  # fmt: skip
        count = len(frame)
        dupes = frame.nisr_code.duplicated().sum()
        level = (
            "pass" if count == BOUNDARY_COUNTS[name] and not dupes and not empty.any() else "fail"
        )
        checks.append(
            Check(key, level, f"{name}: {count} of {BOUNDARY_COUNTS[name]} units, "
                  f"{dupes} duplicate codes, {int(empty.sum())} empty shapes")
        )  # fmt: skip
        frames[name] = frame
    if len(frames) != len(BOUNDARY_FILES):
        return {}, checks
    prov, dist, sect = (frames[n] for n in BOUNDARY_FILES)
    for label, codes, known in (("districts", dist.nisr_code, districts.index),
                                ("sectors", sect.nisr_code, sectors.index)):  # fmt: skip
        outside = sorted(set(codes) - set(known))
        checks.append(
            Check(key, "fail" if outside else "pass", f"{label}: every NISR code is in the "
                  "reviewed crosswalk" if not outside else f"{label}: codes not in the "
                  f"crosswalk: {', '.join(outside[:10])}")
        )  # fmt: skip
    orphans = (~dist.parent_nisr_code.isin(prov.nisr_code)).sum() + (
        ~sect.parent_nisr_code.isin(dist.nisr_code)
    ).sum()
    nested = (sect.nisr_code.str[:4] == sect.parent_nisr_code).all()
    checks.append(
        Check(key, "pass" if not orphans and nested else "fail", f"{orphans} units with a parent "
              "code that does not exist; every sector code starts with its district code"
              if nested else "sector codes do not start with their district code")
    )  # fmt: skip
    gaps = {}
    for name in ("districts.geojson", "sectors.geojson"):
        frame = frames[name].copy()
        lookup = (districts if name == "districts.geojson" else sectors).reindex(frame.nisr_code)
        printed = lookup.source_sector if name == "sectors.geojson" else lookup.source_district
        differ = frame.name.str.casefold().to_numpy() != printed.str.casefold().to_numpy()
        gaps[name] = int(differ.sum())
    checks.append(
        Check(key, "pass", f"names match the crosswalk spelling except {gaps['districts.geojson']} "
              f"district(s) and {gaps['sectors.geojson']} sector(s); units are joined by code, "
              "and the app shows the boundary file's names")
    )  # fmt: skip
    area = sect.to_crs(32735).area.sum() / 1e6
    checks.append(
        Check(key, "pass" if 24_000 < area < 27_000 else "warn", f"sectors cover {area:,.0f} km² "
              "(Rwanda is about 26,300 km² with its lakes)")
    )  # fmt: skip
    overlap = sect.to_crs(32735)
    joined = gpd.sjoin(
        overlap.assign(geometry=overlap.representative_point()),
        dist.to_crs(32735)[["nisr_code", "geometry"]].rename(columns={"nisr_code": "inside"}),
        predicate="within",
    )
    misplaced = (joined.inside != joined.parent_nisr_code).sum()
    checks.append(
        Check(key, "pass" if misplaced == 0 else "warn", f"{misplaced} sectors lie outside the "
              "district their code names")
    )  # fmt: skip
    return frames, checks


# --- run ----------------------------------------------------------------------------------
def classify(files: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {
        "eicv7": [], "mineduc_district": [], "mineduc_national": [], "gazetteer": [],
        "census_sample": [], "projections": [], "boundaries": [], "census_master": [],
        "mineduc_master": [], "mineduc_long": [], "school_points": [],
    }  # fmt: skip
    for path in files:
        if GAZETTEER in path.name and path.suffix == ".xlsx":
            groups["gazetteer"].append(path)
            continue
        sheets = _sheet_names(path) if path.suffix == ".xlsx" else []
        if PROJECTION_SHEET in sheets:
            groups["projections"].append(path)
            continue
        if CENSUS_MASTER_SHEET in sheets:
            groups["census_master"].append(path)
            continue
        if path.name in BOUNDARY_FILES:
            groups["boundaries"].append(path)
            continue
        if path.suffix.lower() == ".geojson" and b"school_category" in path.read_bytes()[:4096]:
            groups["school_points"].append(path)
            continue
        if path.suffix == ".csv":
            head = set(pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns)
            if head >= CENSUS_SAMPLE_COLUMNS:
                groups["census_sample"].append(path)
                continue
            if head >= MINEDUC_MASTER_COLUMNS:
                groups["mineduc_master"].append(path)
                continue
            if path.name in MINEDUC_TABLES and "academic_year" in head:
                groups["mineduc_long"].append(path)  # the validated long layout
                continue
        if path.name == eicv.FILE:
            head = pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns
            if "poverty_rate_percent" in head:
                groups["eicv7"].append(path)
        elif path.name in MINEDUC_TABLES:
            groups["mineduc_district"].append(path)
        elif path.name in MINEDUC_NATIONAL:
            groups["mineduc_national"].append(path)
    return groups


def _sheet_names(path: Path) -> list[str]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        return []
    return load_workbook(path, read_only=True).sheetnames


def _stage(frame: pd.DataFrame, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return target


def run(
    files: list[Path], raw: Path = RAW, interim: Path = INTERIM, manifest: Path = MANIFEST
) -> list[Result]:
    groups = classify(files)
    results = []
    census_total = projected = None
    if groups["census_sample"]:
        path = groups["census_sample"][0]
        receive([path], "census_2022_sample", raw, manifest)
        sectors, districts, checks = census_sample(path)
        staged = None
        previous = raw / census.DATASET.key / "census_2022_sectors.csv"
        if len(sectors) and previous.exists():  # keep sector columns staged from the tables
            kept = pd.read_csv(previous)
            extra = kept[["district_name", "sector_name",
                          *[c for c in MASTER_COLUMNS if c in kept]]]  # fmt: skip
            if extra.shape[1] > 2 and extra.iloc[:, 2:].notna().any().any():
                sectors, districts = merge_census(sectors, extra)
        if len(sectors) and not any(c.level == "fail" for c in checks):
            folder = raw / census.DATASET.key
            _stage(districts, folder / "census_2022_districts.csv")
            staged = _stage(sectors, folder / "census_2022_sectors.csv")
            _mark_staged(manifest, [path], f"data/raw/{census.DATASET.key}/ (weighted sector "
                         "counts; the records stay in _received)")  # fmt: skip
            census_total = int(sectors.children_3_5.sum())
        results.append(Result(census.DATASET.key, checks, staged, None))
    if groups["census_master"]:
        path = groups["census_master"][0]
        receive([path], "census_2022_tables", raw, manifest)
        extra, checks = census_master(path)
        staged = None
        counts = raw / census.DATASET.key / "census_2022_sectors.csv"
        if len(extra) and not any(c.level == "fail" for c in checks):
            if counts.exists():
                sectors, districts = merge_census(pd.read_csv(counts), extra)
                folder = raw / census.DATASET.key
                _stage(districts, folder / "census_2022_districts.csv")
                staged = _stage(sectors, counts)
                _mark_staged(manifest, [path], f"data/raw/{census.DATASET.key}/ (sector columns "
                             "merged with the attendance counts)")  # fmt: skip
            else:
                folder = interim / "census"
                folder.mkdir(parents=True, exist_ok=True)
                extra.to_csv(folder / "census_2022_sector_tables.csv", index=False)
                checks.append(
                    Check(census.DATASET.key, "warn", "not staged: the attendance counts (Table "
                          "2.5 or the sample records) are not staged yet; kept in data/interim/")
                )  # fmt: skip
        results.append(Result(f"{census.DATASET.key} (sector tables)", checks, staged, None))
    if groups["projections"]:
        path = groups["projections"][0]
        receive([path], "nisr_projections", raw, manifest)
        frame, checks = projections_single_age(path)
        staged = None
        if len(frame) and not any(c.level == "fail" for c in checks):
            staged = _stage(frame, raw / projections.DATASET.key / projections.FILE)
            _mark_staged(manifest, [path], f"data/raw/{projections.DATASET.key}/{projections.FILE}")
            projected = frame[frame.year == frame.year.min()].children_3_5.sum()
        results.append(Result(projections.DATASET.key, checks, staged, None))
    if census_total and projected:
        gap = projected / census_total - 1
        results[-1].checks.append(
            Check(projections.DATASET.key, "warn" if abs(gap) > 0.03 else "pass",
                  f"projected children aged 3 to 5 in 2023 ({projected:,}) vs the census sample in "
                  f"2022 ({census_total:,}): {gap:+.1%}. The 2026 estimate takes district totals "
                  "from the projections and only the split across sectors and the attendance "
                  "rate from the census")
        )  # fmt: skip
    if groups["boundaries"]:
        paths = groups["boundaries"]
        receive(paths, "cod_ab_boundaries", raw, manifest)
        frames, checks = boundary_files(paths)
        staged = None
        if frames and not any(c.level == "fail" for c in checks):
            folder = raw / boundaries.DATASET.key
            folder.mkdir(parents=True, exist_ok=True)
            for name, frame in frames.items():
                frame.to_file(folder / name, driver="GeoJSON")
            staged = folder
            _mark_staged(manifest, paths, f"data/raw/{boundaries.DATASET.key}/ (codes, names "
                         "and shapes; other attributes dropped)")  # fmt: skip
        results.append(Result(boundaries.DATASET.key, checks, staged, None))
    if groups["gazetteer"]:
        # Codes only, written to data/reference/ by scripts/import_gazetteer.py (needs openpyxl).
        receive(groups["gazetteer"], "cod_ab_gazetteer", raw, manifest)
        _mark_staged(manifest, groups["gazetteer"], "data/reference/pcodes_cod_ab.csv (codes only)")
    if groups["eicv7"]:
        path = groups["eicv7"][0]
        receive([path], "eicv7", raw, manifest)
        frame, checks = eicv_district(path)
        staged = None
        if not any(c.level == "fail" for c in checks):
            staged = raw / eicv.DATASET.key / eicv.FILE
            staged.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(staged, index=False)
            _mark_staged(manifest, [path], f"data/raw/{eicv.DATASET.key}/{eicv.FILE}")
        results.append(Result(eicv.DATASET.key, checks, staged, None))
    if groups["school_points"]:
        path = groups["school_points"][0]
        receive([path], "mineduc_school_points", raw, manifest)
        checks = school_points(path)
        staged = None
        if not any(c.level == "fail" for c in checks):
            folder = raw / school_source.DATASET.key
            folder.mkdir(parents=True, exist_ok=True)
            staged = folder / school_source.FILE
            shutil.copyfile(path, staged)  # the loader reads the GeoJSON as it is
            _mark_staged(manifest, [path], f"data/raw/{school_source.DATASET.key}/"
                         f"{school_source.FILE} (provisional)")  # fmt: skip
        results.append(Result("schools (distance layer)", checks, staged, None))
    if groups["mineduc_master"]:
        path = groups["mineduc_master"][0]
        receive([path, *groups["mineduc_long"]], "mineduc_master", raw, manifest)
        wide, checks = mineduc_master(path)
        partial = interim / "yearbook" / "mineduc_yearbook_preprimary.partial.csv"
        if len(wide) and partial.exists():
            checks.append(corroborate(wide, pd.read_csv(partial), "the earlier 2024/25 extract"))
        if len(wide) and groups["mineduc_long"]:
            checks.append(corroborate(wide, mineduc_long(groups["mineduc_long"]),
                                      "the validated tables"))  # fmt: skip
        series = interim / "yearbook" / "mineduc_national_series.csv"
        if len(wide) and series.exists():
            checks += cross_checks(wide, pd.read_csv(series))
        staged = None
        gaps = yearbook_gaps(wide) if len(wide) else ["no rows"]
        if gaps:
            checks.append(Check(yearbook.DATASET.key, "warn", f"not staged: {'; '.join(gaps)}"))
        elif not any(c.level == "fail" for c in checks):
            staged = _stage(wide, raw / yearbook.DATASET.key / yearbook.FILE)
            _mark_staged(manifest, [path], f"data/raw/{yearbook.DATASET.key}/{yearbook.FILE}")
            _mark_staged(manifest, groups["mineduc_long"], "cross-check only (agrees with the "
                         "master table)")  # fmt: skip
        results.append(Result(yearbook.DATASET.key, checks, staged, None))
    if groups["mineduc_district"] or groups["mineduc_national"]:
        paths = groups["mineduc_district"] + groups["mineduc_national"]
        receive(paths, "mineduc_yearbook", raw, manifest)
        wide, checks = mineduc_district(groups["mineduc_district"])
        national, more = mineduc_national(groups["mineduc_national"])
        checks += more + cross_checks(wide, national)
        folder = interim / "yearbook"
        folder.mkdir(parents=True, exist_ok=True)
        interim_path = folder / "mineduc_yearbook_preprimary.partial.csv"
        if len(wide):
            wide.to_csv(interim_path, index=False)
        if len(national):
            national.to_csv(folder / "mineduc_national_series.csv", index=False)
        gaps = yearbook_gaps(wide)
        staged = None
        if gaps:
            checks.append(
                Check(yearbook.DATASET.key, "warn", "not staged, the app keeps its labelled "
                      f"stand-in until these arrive: {'; '.join(gaps)}")
            )  # fmt: skip
        elif not any(c.level == "fail" for c in checks):
            staged = raw / yearbook.DATASET.key / yearbook.FILE
            staged.parent.mkdir(parents=True, exist_ok=True)
            wide.to_csv(staged, index=False)
            _mark_staged(manifest, paths, f"data/raw/{yearbook.DATASET.key}/{yearbook.FILE}")
        if not staged:
            _mark_staged(manifest, paths, "data/interim/yearbook/ (incomplete, not loaded)")
        results.append(Result(yearbook.DATASET.key, checks, staged, interim_path))
    return results


def report(results: list[Result]) -> str:
    mark = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
    lines = [f"# Intake report, {date.today().isoformat()}", ""]
    for r in results:
        where = f"staged to {r.staged}" if r.staged else "not staged"
        lines += [f"## {r.dataset}: {where}", ""]
        lines += [f"- {mark[c.level]} {c.text}" for c in r.checks]
        lines.append("")
    return "\n".join(lines)


def _expand(paths: list[str]) -> list[Path]:
    out = []
    for p in map(Path, paths):
        out += sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else [p]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("paths", nargs="+", help="files or folders received")
    args = parser.parse_args()
    files = _expand(args.paths)
    results = run(files)
    if not results:
        print("no recognised files; see the docstring of irerero/data/intake.py")
        return 1
    text = report(results)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text)
    print(text)
    root = DATA.parent
    print(f"Report: {REPORT.relative_to(root)}. Checksums: {MANIFEST.relative_to(root)}.")
    print("Run `make data` to rebuild with whatever was staged.")
    return 1 if any(c.level == "fail" for r in results for c in r.checks) else 0


if __name__ == "__main__":
    sys.exit(main())
