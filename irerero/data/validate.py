"""Check a table against its declared columns. Errors name the file, row and column to fix."""

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from irerero.data.spec import COORDINATE_RANGE, Column

TRUE = {"1", "true", "yes", "y"}
FALSE = {"0", "false", "no", "n"}


class SchemaError(ValueError):
    pass


def _convert(series: pd.Series, column: Column, file: str) -> pd.Series:
    blank = series.isna() | (series.astype(str).str.strip() == "")
    if column.required and blank.any():
        rows = (blank[blank].index[:5] + 2).tolist()
        raise SchemaError(f"{file}: {column.name} is empty on line(s) {rows}")
    values = series.where(~blank)
    if column.type == "text":
        return values.astype("string").str.strip()
    if column.type == "boolean":
        lowered = values.astype("string").str.strip().str.lower()
        bad = ~blank & ~lowered.isin(TRUE | FALSE)
        if bad.any():
            raise SchemaError(f"{file}: {column.name} must be yes or no (line {bad.idxmax() + 2})")
        return lowered.map(lambda v: None if pd.isna(v) else v in TRUE)
    if column.type == "date":
        parsed = pd.to_datetime(values, errors="coerce", format="%Y-%m-%d")
        bad = ~blank & parsed.isna()
        if bad.any():
            raise SchemaError(f"{file}: {column.name} must be YYYY-MM-DD (line {bad.idxmax() + 2})")
        return parsed.dt.date
    numbers = pd.to_numeric(values.astype("string").str.replace(",", ""), errors="coerce")
    bad = ~blank & numbers.isna()
    if bad.any():
        raise SchemaError(f"{file}: {column.name} is not a number (line {bad.idxmax() + 2})")
    if column.type in COORDINATE_RANGE:
        low, high = COORDINATE_RANGE[column.type]
        outside = ~blank & ((numbers < low) | (numbers > high))
        if outside.any():
            raise SchemaError(
                f"{file}: {column.name} must be a {column.type} inside Rwanda ({low} to {high}); "
                f"check for swapped lon/lat (line {outside.idxmax() + 2})"
            )
        return numbers.astype("Float64")
    if (numbers < 0).any():
        raise SchemaError(f"{file}: {column.name} cannot be negative (line {numbers.idxmin() + 2})")
    if column.type == "share" and (numbers > 1).any():
        raise SchemaError(
            f"{file}: {column.name} is a share between 0 and 1; write 38.8% as 0.388 "
            f"(line {numbers.idxmax() + 2})"
        )
    if column.type == "integer":
        return numbers.round().astype("Int64")
    return numbers.astype("Float64")


def validate(frame: pd.DataFrame, columns: Sequence[Column], file: str) -> pd.DataFrame:
    """Only the declared columns, converted to their types."""
    missing = [c.name for c in columns if c.required and c.name not in frame.columns]
    if missing:
        raise SchemaError(f"{file}: missing column(s) {', '.join(missing)}")
    if frame.empty:
        raise SchemaError(f"{file}: no rows")
    out = pd.DataFrame(index=frame.index)
    for column in columns:
        if column.name in frame.columns:
            out[column.name] = _convert(frame[column.name], column, file)
        else:
            out[column.name] = pd.NA
    return out.reset_index(drop=True)


def read_csv(path: Path, columns: Sequence[Column]) -> pd.DataFrame:
    return validate(pd.read_csv(path, dtype=str, encoding="utf-8-sig"), columns, path.name)
