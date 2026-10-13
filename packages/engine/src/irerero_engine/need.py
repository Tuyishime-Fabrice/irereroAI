"""NeedEstimator: children, stunting risk and mothers' childcare barrier per area, with ranges.

Phase 1 baseline: returns stored estimates (simulated by the demo generator).
Phase 2: a small-area model over area_indicator, calibrated to official district totals,
implements the same interface.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from irerero_engine.types import Driver, Range, SourceRef


@dataclass(frozen=True)
class AreaNeed:
    area_code: str
    children_0_2: Range
    children_3_6: Range
    stunting_risk: Range
    mothers_barrier_share: Range
    drivers: tuple[Driver, ...]
    sources: tuple[SourceRef, ...]
    model_version: str

    @property
    def children(self) -> Range:
        return Range(
            self.children_0_2.estimate + self.children_3_6.estimate,
            self.children_0_2.low + self.children_3_6.low,
            self.children_0_2.high + self.children_3_6.high,
        )

    @property
    def relative_uncertainty(self) -> float:
        """Half-width of the widest interval relative to its estimate, 0 when certain.

        Drives the hatching density on maps.
        """
        widths = []
        for value in (self.children, self.stunting_risk):
            if value.estimate > 0:
                widths.append((value.high - value.low) / 2 / value.estimate)
        return max(widths, default=0.0)


class NeedEstimator(Protocol):
    version: str

    def estimate(self, area_codes: Sequence[str]) -> dict[str, AreaNeed]: ...


class StoredNeedEstimator:
    """Baseline: reads need_estimate rows through a loader supplied by the caller."""

    version = "need-stored-1"

    def __init__(self, load: Callable[[Sequence[str]], Mapping[str, AreaNeed]]) -> None:
        self._load = load

    def estimate(self, area_codes: Sequence[str]) -> dict[str, AreaNeed]:
        return dict(self._load(area_codes))
