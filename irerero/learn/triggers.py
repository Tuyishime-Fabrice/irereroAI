"""Training triggers: a check-in with no water flags the WASH course; fewer than three meal days
flags the nutrition course; a sector with weak water and sanitation, or high stunting, flags
them for every caregiver in the sector. Flags are recommendations until an officer confirms.
"""

import pandas as pd
from sqlalchemy import Engine

from irerero.config import WEAK_FACTOR
from irerero.learn import checkins, progress


def sector_flags(diagnosis: pd.DataFrame) -> dict[str, set[str]]:
    """geo_id -> {"WASH", "STUNTING"} from the diagnosis factor parts."""
    flags: dict[str, set[str]] = {}
    for row in diagnosis.itertuples():
        found = set()
        wash = max(getattr(row, "home_water", 0) or 0, getattr(row, "home_sanitation", 0) or 0)
        if wash >= WEAK_FACTOR:
            found.add("WASH")
        if (getattr(row, "wellbeing", 0) or 0) >= WEAK_FACTOR:
            found.add("STUNTING")
        if found:
            flags[row.geo_id] = found
    return flags


def run(eng: Engine, diagnosis: pd.DataFrame | None = None) -> list[tuple[str, str, str]]:
    """Add recommended assignments for every trigger that fires. Returns the new flags."""
    carers = progress.caregivers(eng)
    latest = checkins.problems(checkins.frame(eng, carers.centre_id.dropna().tolist()))
    by_centre = latest.set_index("centre_id") if len(latest) else pd.DataFrame()
    sectors = sector_flags(diagnosis) if diagnosis is not None else {}
    added = []
    for carer in carers.itertuples():
        wanted: list[tuple[str, str]] = []
        if carer.centre_id in by_centre.index:
            row = by_centre.loc[carer.centre_id]
            if row.no_water:
                wanted.append(("wash", "checkin:no_water"))
            if row.few_meals:
                wanted.append(("nutrition", "checkin:few_meals"))
        for flag in sorted(sectors.get(carer.sector_id, set())):
            wanted.append(("wash" if flag == "WASH" else "nutrition", f"sector:{flag}"))
        for course_id, trigger in wanted:
            if progress.recommend(eng, carer.caregiver_id, course_id, trigger):
                added.append((carer.caregiver_id, course_id, trigger))
    return added
