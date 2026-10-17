"""Write analysis tables (replacing them) and read any table back as a DataFrame."""

import math
from collections.abc import Mapping
from typing import Any

import pandas as pd
from sqlalchemy import Engine, delete, insert, select

from irerero.db.models import ANALYSIS_TABLES, Base


def _clean(value: Any) -> Any:
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item") and not isinstance(value, (list, dict)):
        return value.item()
    return value


def replace_analysis(eng: Engine, frames: Mapping[str, pd.DataFrame]) -> None:
    """Empty every analysis table, then insert the given frames. App tables are untouched."""
    tables = {t.__tablename__: t.__table__ for t in ANALYSIS_TABLES}
    unknown = set(frames) - set(tables)
    if unknown:
        raise ValueError(f"not analysis tables: {sorted(unknown)}")
    with eng.begin() as conn:
        for model in ANALYSIS_TABLES:  # children first, so foreign keys allow the delete
            conn.execute(delete(model.__table__))
        for model in reversed(ANALYSIS_TABLES):
            name = model.__tablename__
            if name not in frames or frames[name].empty:
                continue
            columns = [c.name for c in tables[name].columns]
            records = [
                {k: _clean(v) for k, v in row.items() if k in columns}
                for row in frames[name].to_dict(orient="records")
            ]
            for start in range(0, len(records), 5000):
                conn.execute(insert(tables[name]), records[start : start + 5000])


def read(eng: Engine, table: str, **where: Any) -> pd.DataFrame:
    model = Base.metadata.tables[table]
    query = select(model)
    for column, value in where.items():
        query = query.where(model.c[column] == value)
    with eng.connect() as conn:
        return pd.DataFrame(conn.execute(query).mappings().all(), columns=[c.name for c in model.c])
