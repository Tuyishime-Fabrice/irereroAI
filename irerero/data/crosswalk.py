"""Names in each source mapped to geo_id through a reviewed CSV. No fuzzy matching at run time.

data/reference/sector_name_crosswalk.csv has one row per (source, district, sector name) as
printed in that source. source "*" applies to every source that spells the name the same way.
When a source spells a name differently, add a row for that source; the loader stops with the
list of unmatched names until every one is in the file.
"""

from functools import lru_cache

import pandas as pd

from irerero.config import REFERENCE
from irerero.data.validate import SchemaError

FILE = REFERENCE / "sector_name_crosswalk.csv"
DISTRICT_FILE = REFERENCE / "district_name_crosswalk.csv"


def _key(text: str) -> str:
    # Case and spacing only: spelling differences must be reviewed into the crosswalk.
    return " ".join(str(text).split()).casefold()


@lru_cache
def _sectors() -> dict[tuple[str, str, str], str]:
    frame = pd.read_csv(FILE, dtype=str).fillna("")
    return {
        (row.source, _key(row.source_district), _key(row.source_sector)): row.geo_id
        for row in frame.itertuples()
    }


@lru_cache
def _districts() -> dict[tuple[str, str], str]:
    frame = pd.read_csv(DISTRICT_FILE, dtype=str).fillna("")
    return {(row.source, _key(row.source_district)): row.geo_id for row in frame.itertuples()}


def sector_ids(source: str, districts: pd.Series, sectors: pd.Series) -> pd.Series:
    table = _sectors()
    ids, missing = [], []
    for district, sector in zip(districts, sectors, strict=True):
        key = (_key(district), _key(sector))
        found = table.get((source, *key)) or table.get(("*", *key))
        if found is None:
            missing.append(f"{district} / {sector}")
        ids.append(found)
    if missing:
        raise SchemaError(
            f"{source}: {len(missing)} sector name(s) are not in "
            f"data/reference/sector_name_crosswalk.csv: {', '.join(sorted(set(missing))[:10])}"
        )
    return pd.Series(ids, index=sectors.index)


def district_ids(source: str, districts: pd.Series) -> pd.Series:
    table = _districts()
    ids, missing = [], []
    for district in districts:
        found = table.get((source, _key(district))) or table.get(("*", _key(district)))
        if found is None:
            missing.append(str(district))
        ids.append(found)
    if missing:
        raise SchemaError(
            f"{source}: district name(s) not in data/reference/district_name_crosswalk.csv: "
            f"{', '.join(sorted(set(missing)))}"
        )
    return pd.Series(ids, index=districts.index)
