"""Value types shared by every engine interface. Coordinates are metres in EPSG:32735."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Range:
    estimate: float
    low: float
    high: float

    def scaled(self, factor: float) -> "Range":
        return Range(self.estimate * factor, self.low * factor, self.high * factor)


@dataclass(frozen=True)
class Driver:
    feature: str
    label_en: str
    label_rw: str
    contribution: float


@dataclass(frozen=True)
class SourceRef:
    """An input an output was computed from: shown as a source chip in the UI."""

    table: str
    source: str
    reference_year: int
    origin: str


@dataclass(frozen=True)
class Position:
    x: float
    y: float

    def distance_to(self, other: "Position") -> float:
        return float(((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5)
