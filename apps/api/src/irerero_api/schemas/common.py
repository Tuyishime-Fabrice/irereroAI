from collections.abc import Iterable
from typing import TypeVar

from pydantic import BaseModel, Field

from irerero_contract.enums import Origin
from irerero_engine.types import Driver, Range, SourceRef

T = TypeVar("T")


class SourceOut(BaseModel):
    table: str
    source: str
    reference_year: int
    origin: Origin


class Provenance(BaseModel):
    """Every origin and source behind the data in a response. The UI shows the simulated
    label whenever `origins` contains "simulated"."""

    origins: list[Origin]
    sources: list[SourceOut]


class Envelope[T](BaseModel):
    data: T
    provenance: Provenance


def provenance(sources: Iterable[SourceRef]) -> Provenance:
    unique = sorted(
        {(s.table, s.source, s.reference_year, s.origin) for s in sources},
        key=lambda s: (s[0], s[1]),
    )
    return Provenance(
        origins=sorted({Origin(s[3]) for s in unique}, key=lambda o: o.value),
        sources=[
            SourceOut(table=t, source=src, reference_year=y, origin=Origin(o))
            for t, src, y, o in unique
        ],
    )


def wrap[T](data: T, sources: Iterable[SourceRef]) -> Envelope[T]:
    return Envelope[T](data=data, provenance=provenance(sources))


class RangeOut(BaseModel):
    estimate: float
    low: float
    high: float

    @classmethod
    def of(cls, value: Range) -> "RangeOut":
        return cls(estimate=value.estimate, low=value.low, high=value.high)


class DriverOut(BaseModel):
    feature: str
    label_en: str
    label_rw: str
    contribution: float

    @classmethod
    def of(cls, driver: Driver) -> "DriverOut":
        return cls(
            feature=driver.feature,
            label_en=driver.label_en,
            label_rw=driver.label_rw,
            contribution=driver.contribution,
        )


class PublicCount(BaseModel):
    """A count on a public page. Below 5 it is withheld: value is null, suppressed is true."""

    value: int | None
    suppressed: bool


class Message(BaseModel):
    detail: str


class Issue(BaseModel):
    code: str
    field: str
    params: dict[str, float] = Field(default_factory=dict)
