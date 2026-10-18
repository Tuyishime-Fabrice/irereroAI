"""Places, rooms and caregivers needed to reach a target attendance rate.

    places     = max(0, ceil(t * P) - A)
    rooms      = ceil(places / 30)                    30 children per room
    caregivers = ceil(places / 30) to ceil(places / 15)   ratios 1:30 to 1:15

P is the 2026 estimate of children aged 3 to 5 and A the estimate of those attending.
Norms from the National ECD Standards (2024), see irerero.config.
"""

import math

import numpy as np
import pandas as pd

from irerero.config import CAREGIVER_RATIO_HIGH, CAREGIVER_RATIO_LOW, CHILDREN_PER_ROOM


def _ceil(x: float) -> int:
    # round first so 0.65 * 100 = 65.00000000000001 is 65, not 66
    return math.ceil(round(x, 6))


def places(target: float, children: float, attending: float) -> int:
    return max(0, _ceil(target * children) - _ceil(attending))


def rooms(n_places: int) -> int:
    return _ceil(n_places / CHILDREN_PER_ROOM.value)


def caregivers(n_places: int) -> tuple[int, int]:
    """(low, high): at 1 per 30 children and at 1 per 15."""
    return _ceil(n_places / CAREGIVER_RATIO_HIGH.value), _ceil(n_places / CAREGIVER_RATIO_LOW.value)


def needs(frame: pd.DataFrame, target: float) -> pd.DataFrame:
    """Adds places, rooms, caregivers_low and caregivers_high to a frame with children_3_5 and
    attending."""
    rounded = np.ceil((target * frame.children_3_5.astype(float)).round(6))
    n = (rounded - np.ceil(frame.attending.astype(float).round(6))).clip(lower=0).astype(int)
    out = frame.assign(places=n)
    out["rooms"] = np.ceil(n / CHILDREN_PER_ROOM.value).astype(int)
    out["caregivers_low"] = np.ceil(n / CAREGIVER_RATIO_HIGH.value).astype(int)
    out["caregivers_high"] = np.ceil(n / CAREGIVER_RATIO_LOW.value).astype(int)
    return out
