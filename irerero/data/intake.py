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
poverty_rate_percent) and the MINEDUC yearbook district tables (preprimary_*_by_district.csv)
with their national series.
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

from irerero.config import DATA, INTERIM, RAW, YEARBOOK_YEARS
from irerero.data.crosswalk import district_ids
from irerero.data.sources import eicv, yearbook
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


# --- run ----------------------------------------------------------------------------------
def classify(files: list[Path]) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {
        "eicv7": [], "mineduc_district": [], "mineduc_national": [], "gazetteer": []
    }  # fmt: skip
    for path in files:
        if GAZETTEER in path.name and path.suffix == ".xlsx":
            groups["gazetteer"].append(path)
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


def run(
    files: list[Path], raw: Path = RAW, interim: Path = INTERIM, manifest: Path = MANIFEST
) -> list[Result]:
    groups = classify(files)
    results = []
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
