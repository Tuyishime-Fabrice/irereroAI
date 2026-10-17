"""Loaders: schema errors name the file, column and line; real files win over the demo copy;
names join only through the reviewed crosswalk."""

import re
import shutil

import pandas as pd
import pytest

from irerero.config import DEMO, OBSERVED, PUBLISHED
from irerero.data import crosswalk
from irerero.data.sources import census, rdhs
from irerero.data.spec import Column
from irerero.data.validate import SchemaError, validate


def frame(**columns):
    return pd.DataFrame({k: [str(v) for v in vs] for k, vs in columns.items()})


@pytest.mark.parametrize(
    ("column", "values", "message"),
    [
        (Column("n", "integer", ""), ["5", "-1"], "cannot be negative (line 3)"),
        (Column("n", "integer", ""), ["5", "x"], "is not a number (line 3)"),
        (Column("s", "share", ""), ["0.4", "38.8"], "write 38.8% as 0.388"),
        (Column("lat", "latitude", ""), ["-1.9", "1.9"], "swapped lon/lat (line 3)"),
        (Column("lon", "longitude", ""), ["30.1", "-1.9"], "inside Rwanda"),
        (Column("d", "date", ""), ["2026-09-30", "30/09/2026"], "YYYY-MM-DD"),
        (Column("b", "boolean", ""), ["yes", "maybe"], "yes or no"),
        (Column("t", "text", ""), ["a", ""], "empty on line(s) [3]"),
    ],
)
def test_schema_errors(column, values, message):
    with pytest.raises(SchemaError, match=re.escape(message)):
        validate(frame(**{column.name: values}), [column], "f.csv")


def test_converts_types_and_fills_optional_columns():
    out = validate(
        frame(n=["1,250", "3"], lat=["-1.95", "-2.5"], ok=["yes", "no"]),
        [
            Column("n", "integer", ""),
            Column("lat", "latitude", ""),
            Column("ok", "boolean", ""),
            Column("extra", "number", "", required=False),
        ],
        "f.csv",
    )
    assert out.n.tolist() == [1250, 3]
    assert out.lat.tolist() == [-1.95, -2.5]
    assert out.ok.tolist() == [True, False]
    assert out.extra.isna().all()


def test_missing_column_is_named():
    with pytest.raises(SchemaError, match="missing column"):
        validate(frame(a=["1"]), [Column("b", "integer", "")], "f.csv")


def test_unmatched_sector_name_stops_the_load():
    with pytest.raises(SchemaError, match="Gicumbi / Byumbaa"):
        crosswalk.sector_ids("census_2022", pd.Series(["Gicumbi"]), pd.Series(["Byumbaa"]))


def test_crosswalk_ignores_case_and_spacing_only():
    ids = crosswalk.sector_ids("x", pd.Series(["  gicumbi "]), pd.Series(["BYUMBA"]))
    assert ids.tolist() == ["S-GICUMBI-BYUMBA"]


def test_real_file_wins_and_keeps_its_status(tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(DEMO / "rdhs_2025", raw / "rdhs_2025")
    loaded = rdhs.load(raw)
    assert loaded.real
    assert loaded.status == PUBLISHED

    shutil.copytree(DEMO / "census_2022", raw / "census_2022")
    sectors, _ = census.load(raw)
    assert sectors.real
    assert sectors.status == OBSERVED


def test_census_rejects_inconsistent_rows(tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(DEMO / "census_2022", raw / "census_2022")
    path = raw / "census_2022" / "census_2022_sectors.csv"
    rows = pd.read_csv(path, dtype=str)
    rows.loc[0, "children_3_5"] = str(int(rows.loc[0, "children_3_5"]) + 1)
    rows.to_csv(path, index=False)
    with pytest.raises(SchemaError, match="attending \\+ never attended"):
        census.load(raw)
