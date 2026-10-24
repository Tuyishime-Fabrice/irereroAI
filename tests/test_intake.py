"""Intake of received files: originals kept read-only with a checksum, conversion to the
declared schemas, quality checks, and staging only when a dataset is complete. The fixtures
are made-up numbers in the received formats, not the real files."""

import stat
from pathlib import Path

import pandas as pd
import pytest

from irerero.data import intake
from irerero.data.sources import eicv, yearbook
from irerero.data.sources.base import folder

DISTRICTS = pd.read_csv("data/reference/district_name_crosswalk.csv").source_district.tolist()


def _eicv(path: Path, rates: list[float] | None = None) -> Path:
    rates = rates or [10 + i for i in range(30)]
    pd.DataFrame(
        {
            "district": DISTRICTS,
            "poverty_rate_percent": rates,
            "year": "2023/24",
            "indicator": "Headcount poverty rate",
            "geographic_level": "District",
            "source": "NISR, EICV7 Main Indicators Report 2023-24, Figure 9.1",
            "source_note": "made-up test values",
        }
    ).to_csv(path / "eicv7_poverty.csv", index=False)
    return path / "eicv7_poverty.csv"


def _pupils(path: Path, nyarugenge_total: int | None = None) -> Path:
    """Two provinces' worth of rows is enough to check the aggregate logic."""
    rows = [[d, 100, 100, 200, 110, 110, 220] for d in DISTRICTS]
    frame = pd.DataFrame(
        rows,
        columns=["district_or_aggregate", "boys_2023_24", "girls_2023_24", "total_2023_24",
                 "boys_2024_25", "girls_2024_25", "total_2024_25"],
    )  # fmt: skip
    if nyarugenge_total is not None:
        frame.loc[frame.district_or_aggregate == "Nyarugenge", "total_2023_24"] = nyarugenge_total
    total = frame.drop(columns="district_or_aggregate").sum()
    national = pd.DataFrame([["Rwanda", *total.tolist()]], columns=frame.columns)
    pd.concat([frame, national]).to_csv(path / "preprimary_pupils_by_district.csv", index=False)
    return path / "preprimary_pupils_by_district.csv"


@pytest.fixture
def dirs(tmp_path: Path) -> dict[str, Path]:
    out = {k: tmp_path / k for k in ("in", "raw", "interim")}
    for p in out.values():
        p.mkdir()
    out["manifest"] = tmp_path / "received_files.csv"
    return out


def _run(dirs: dict[str, Path], files: list[Path]) -> list[intake.Result]:
    return intake.run(files, dirs["raw"], dirs["interim"], dirs["manifest"])


def test_eicv_district_is_converted_staged_and_loads(dirs):
    src = _eicv(dirs["in"])
    (result,) = _run(dirs, [src])
    assert result.staged == dirs["raw"] / "eicv7" / eicv.FILE
    assert not [c for c in result.checks if c.level == "fail"]
    loaded = eicv.load(dirs["raw"])
    assert loaded.real and loaded.status == eicv.DATASET.status
    assert loaded.frame.level.eq("district").all() and loaded.frame.geo_id.notna().all()
    assert loaded.frame.poverty_rate.max() == pytest.approx(0.39)  # percent became a share


def test_original_is_kept_read_only_with_its_checksum(dirs):
    src = _eicv(dirs["in"])
    _run(dirs, [src])
    _run(dirs, [src])  # receiving the same file twice records it once
    kept = dirs["raw"] / "_received" / "eicv7" / "eicv7_poverty.csv"
    assert kept.read_bytes() == src.read_bytes()
    assert not kept.stat().st_mode & stat.S_IWUSR
    manifest = pd.read_csv(dirs["manifest"])
    assert len(manifest) == 1 and manifest.sha256.iat[0] == intake.sha256(src)
    assert manifest.staged_as.iat[0] == "data/raw/eicv7/eicv7_poverty.csv"


def test_eicv_flags_ties_and_rejects_percent_out_of_range(dirs):
    rates = [10 + i for i in range(30)]
    rates[1] = rates[0]
    (result,) = _run(dirs, [_eicv(dirs["in"], rates)])
    assert any("re-check" in c.text for c in result.checks)
    rates[2] = 140
    (bad,) = _run(dirs, [_eicv(dirs["in"], rates)])
    assert any(c.level == "fail" for c in bad.checks)


def test_partial_yearbook_stays_in_interim_and_names_the_gaps(dirs):
    (result,) = _run(dirs, [_pupils(dirs["in"])])
    assert result.staged is None
    assert not yearbook.DATASET.present(dirs["raw"])
    assert folder(yearbook.DATASET, dirs["raw"])[1] is False  # the app keeps its stand-in
    partial = pd.read_csv(result.interim)
    assert set(partial.school_year) == {"2023/24", "2024/25"} and partial.pupils.notna().all()
    assert partial.teachers.isna().all()  # nothing is filled in
    gaps = next(c.text for c in result.checks if c.text.startswith("not staged"))
    assert "2020/21: no district table" in gaps and "teachers" in gaps


def test_yearbook_totals_that_do_not_add_up_are_reported(dirs):
    (result,) = _run(dirs, [_pupils(dirs["in"], nyarugenge_total=230)])
    fails = [c.text for c in result.checks if c.level == "fail"]
    assert any("Nyarugenge 2023/24" in t and "200" in t for t in fails)
    (small,) = _run(dirs, [_pupils(dirs["in"], nyarugenge_total=201)])
    assert any("Nyarugenge" in c.text and c.level == "warn" for c in small.checks)


def test_crosswalk_codes_are_complete_unique_and_nested():
    sectors = pd.read_csv("data/reference/sector_name_crosswalk.csv", dtype=str)
    districts = pd.read_csv("data/reference/district_name_crosswalk.csv", dtype=str)
    canon = sectors[sectors.source == "*"]
    assert canon.nisr_sector_code.notna().all() and canon.nisr_sector_code.is_unique
    assert districts.nisr_district_code.notna().all() and districts.nisr_district_code.is_unique
    # a sector's code starts with its district's code (RW27 -> RW2701)
    parent = dict(zip(districts.source_district, districts.nisr_district_code, strict=True))
    assert all(
        code.startswith(parent[d])
        for code, d in zip(canon.nisr_sector_code, canon.source_district, strict=True)
    )


def test_templates_match_the_loader_declarations():
    from irerero.data.__main__ import TEMPLATES, template_headers

    for name, header in template_headers().items():
        assert (TEMPLATES / name).read_text().strip() == header, (
            f"run python -m irerero.data --templates ({name})"
        )


def test_yearbooks_that_repeat_a_year_merge_and_disagreements_fail(dirs):
    first, second = dirs["in"] / "a", dirs["in"] / "b"
    first.mkdir()
    second.mkdir()
    same = intake.run(
        [_pupils(first), _pupils(second)], dirs["raw"], dirs["interim"], dirs["manifest"]
    )
    assert not [c for c in same[0].checks if "disagree" in c.text]
    kept = list((dirs["raw"] / "_received" / "mineduc_yearbook").iterdir())
    assert len(kept) == 1  # the identical second copy is recorded once
    _pupils(second, nyarugenge_total=201)
    clash = intake.run([_pupils(first), second / "preprimary_pupils_by_district.csv"],
                       dirs["raw"], dirs["interim"], dirs["manifest"])  # fmt: skip
    assert any("two files disagree" in c.text for c in clash[0].checks)
    assert len(list((dirs["raw"] / "_received" / "mineduc_yearbook").iterdir())) == 2


# --- census sample, projections, boundaries --------------------------------------------------
SECTORS = pd.read_csv("data/reference/sector_name_crosswalk.csv", dtype=str)
SECTORS = SECTORS[SECTORS.source == "*"]


def _census_sample(path: Path, drop: int = 0) -> Path:
    """Made-up records: per sector two attending children (weight 10) and one never attended
    (weight 5), and one record with attendance not stated."""
    rows = []
    for code in SECTORS.nisr_sector_code.iloc[drop:]:
        sector = int(code.removeprefix("RW"))
        for age, attendance, weight in ((3, 2, 10.0), (4, 2, 10.0), (5, 3, 5.0)):
            rows.append([sector // 100, sector, age, attendance, weight])
    rows.append([11, 1101, 3, 9, 7.0])
    frame = pd.DataFrame(rows, columns=["district_code", "sector_code", "age_years",
                                        "attendance_code", "population_weight"])  # fmt: skip
    frame.to_csv(path / "children_age_3_5.csv", index=False)
    return path / "children_age_3_5.csv"


def test_census_records_become_weighted_sector_counts_and_nothing_else(dirs):
    (result,) = _run(dirs, [_census_sample(dirs["in"])])
    assert result.staged is not None, [c.text for c in result.checks]
    staged = pd.read_csv(result.staged)
    assert len(staged) == 416 and set(staged.basis) == {"sample"}
    assert (staged.children_3_5_attending == 20).all() and (
        staged.children_3_5_never_attended == 5
    ).all()
    assert (staged.children_3_5 == 25).all()  # the unstated record is left out, and said so
    assert any("attendance not stated" in c.text for c in result.checks)
    # only counts are staged: no record, weight or age reaches data/raw/<dataset>/
    assert not {"population_weight", "age_years", "attendance_code"} & set(staged.columns)
    original = next((dirs["raw"] / "_received" / "census_2022_sample").iterdir())
    assert not original.stat().st_mode & stat.S_IWUSR
    from irerero.config import MODEL
    from irerero.data.sources import census

    sectors, districts = census.load(dirs["raw"])
    assert sectors.real and sectors.status == MODEL  # weighted from a sample: a model estimate
    assert districts.frame.children_3_5.sum() == staged.children_3_5.sum()


def test_census_records_missing_sectors_are_not_staged(dirs):
    (result,) = _run(dirs, [_census_sample(dirs["in"], drop=3)])
    assert result.staged is None
    assert any(c.level == "fail" and "413 of 416" in c.text for c in result.checks)


def _projection_sheets(off_by: int = 0) -> dict[str, pd.DataFrame]:
    rows = []
    for d in DISTRICTS:
        for year in range(2023, 2033):
            for age in [*map(str, range(80)), "80+"]:
                female, male = (
                    50,
                    50 + (off_by if (d, year, age) == (DISTRICTS[0], 2023, "4") else 0),
                )
                rows += [[d, year, age, "Female", female], [d, year, age, "Male", male],
                         [d, year, age, "Both sexes", 100]]  # fmt: skip
    long = pd.DataFrame(rows, columns=["district", "year", "age", "sex", "population"])
    return {intake.PROJECTION_SHEET: long}


def test_single_age_projections_give_population_and_children_3_5():
    frame, checks = intake.projections_from_sheets(_projection_sheets())
    assert not [c for c in checks if c.level == "fail"]
    assert len(frame) == 300 and (frame.population == 8100).all()
    assert (frame.children_3_5 == 300).all()  # ages 3, 4 and 5, both sexes


def test_single_age_projections_that_do_not_add_up_fail():
    _, checks = intake.projections_from_sheets(_projection_sheets(off_by=3))
    assert any(c.level == "fail" and "female + male" in c.text for c in checks)
