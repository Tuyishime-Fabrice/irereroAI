"""Load every dataset once. The rest of the pipeline only sees this object."""

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

from irerero.config import PROVISIONAL, RAW
from irerero.data.sources import (
    boundaries,
    census,
    eicv,
    ncda,
    osm,
    projections,
    rdhs,
    schools,
    worldpop,
)
from irerero.data.sources import yearbook as yearbook_source
from irerero.data.sources.base import Loaded


@dataclass
class Inputs:
    units: dict[str, gpd.GeoDataFrame]
    boundary_source: str
    boundaries_real: bool
    census_sectors: Loaded
    census_districts: Loaded
    projections: Loaded
    yearbook: Loaded
    stunting: Loaded
    poverty: Loaded
    supply: Loaded
    schools: osm.Network
    under5: pd.Series | None
    raw: Path

    @property
    def sectors(self) -> gpd.GeoDataFrame:
        return self.units["sector"]

    @property
    def districts(self) -> gpd.GeoDataFrame:
        return self.units["district"]


def school_network(raw: Path = RAW) -> osm.Network:
    """The schools for the distance layer: OpenStreetMap (with roads) when its extract is
    loaded; otherwise the MINEDUC school list, labelled provisional while it is partial;
    otherwise the simulated stand-in. A school file with no usable point falls back to the
    stand-in, and its report says why."""
    if osm.DATASET.present(raw):
        return osm.load(raw)
    listed = schools.load(raw)
    if listed is None:
        return osm.load(raw)
    frame, report = listed
    if report.loaded:
        return osm.Network(schools=frame, status=PROVISIONAL, real=True, source=schools.SOURCE,
                           report=report.as_dict())  # fmt: skip
    fallback = osm.load(raw)
    fallback.report = report.as_dict()
    return fallback


def load_inputs(raw: Path = RAW) -> Inputs:
    units, boundary_source, real = boundaries.load(raw)
    sectors, districts = census.load(raw)
    return Inputs(
        units=units,
        boundary_source=boundary_source,
        boundaries_real=real,
        census_sectors=sectors,
        census_districts=districts,
        projections=projections.load(raw),
        yearbook=yearbook_source.load(raw),
        stunting=rdhs.load(raw),
        poverty=eicv.load(raw),
        supply=ncda.load(raw),
        schools=school_network(raw),
        under5=worldpop.under5_by_sector(units["sector"], raw),
        raw=raw,
    )
