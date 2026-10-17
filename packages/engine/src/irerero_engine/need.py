"""NeedEstimator: children, stunting risk and mothers' childcare barrier per area, with ranges.

Phase 1: LayeredNeedEstimator uses official values where their files are loaded and the
simulated estimate everywhere else, saying which is which. Phase 2: a small-area model over
area_indicator, calibrated to official district totals, implements the same interface.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from irerero_engine.types import Range, SourceRef

# Census counts describe 2022; children born or moved since then widen the range.
CENSUS_DRIFT = 0.05
# No survey publishes sector stunting or barrier values. A sector takes its district's value,
# with the interval widened by this factor and never narrower than MIN_SECTOR_HALF_WIDTH.
DISTRICT_TO_SECTOR = 1.5
MIN_SECTOR_HALF_WIDTH = 0.05


@dataclass(frozen=True)
class AreaNeed:
    area_code: str
    children_0_2: Range
    children_3_6: Range
    stunting_risk: Range
    mothers_barrier_share: Range
    sources: tuple[SourceRef, ...]
    """One per component: children, stunting risk, mothers' barrier."""
    model_version: str

    @property
    def simulated(self) -> bool:
        return any(s.origin == "simulated" for s in self.sources)

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


@dataclass(frozen=True)
class Loaded:
    """An official value for an area, with the source it came from."""

    value: Range
    source: SourceRef


def _widened(value: Range) -> Range:
    half = max((value.high - value.low) / 2 * DISTRICT_TO_SECTOR, MIN_SECTOR_HALF_WIDTH)
    return Range(value.estimate, max(0.0, value.estimate - half), min(1.0, value.estimate + half))


def _counted(count: float) -> Range:
    return Range(count, count * (1 - CENSUS_DRIFT), count * (1 + CENSUS_DRIFT))


class LayeredNeedEstimator:
    """Official values over a base estimate, component by component.

    children: the area's own census counts. stunting and barrier: the area's own survey value,
    or, for a sector, its district's value with a wider interval.
    """

    version = "need-layered-1"

    def __init__(
        self,
        base: Mapping[str, AreaNeed],
        parents: Mapping[str, str],
        children_0_2: Mapping[str, Loaded],
        children_3_6: Mapping[str, Loaded],
        stunting: Mapping[str, Loaded],
        barrier: Mapping[str, Loaded],
    ) -> None:
        self.base = base
        self.parents = parents
        self.children_0_2 = children_0_2
        self.children_3_6 = children_3_6
        self.stunting = stunting
        self.barrier = barrier

    def _share(self, values: Mapping[str, Loaded], area: str) -> Loaded | None:
        if area in values:
            return values[area]
        parent = self.parents.get(area)
        if parent in values:
            found = values[parent]
            return Loaded(_widened(found.value), found.source)
        return None

    def estimate(self, area_codes: Sequence[str]) -> dict[str, AreaNeed]:
        out = {}
        for code in area_codes:
            need = self.base[code]
            children_source, stunting_source, barrier_source = need.sources
            young, old = self.children_0_2.get(code), self.children_3_6.get(code)
            if young and old:
                need = replace(
                    need,
                    children_0_2=_counted(young.value.estimate),
                    children_3_6=_counted(old.value.estimate),
                )
                children_source = young.source
            stunting = self._share(self.stunting, code)
            if stunting:
                need = replace(need, stunting_risk=stunting.value)
                stunting_source = stunting.source
            barrier = self._share(self.barrier, code)
            if barrier:
                need = replace(need, mothers_barrier_share=barrier.value)
                barrier_source = barrier.source
            out[code] = replace(
                need,
                sources=(children_source, stunting_source, barrier_source),
                model_version=self.version,
            )
        return out
