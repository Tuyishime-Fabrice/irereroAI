"""Load every dataset once. The rest of the pipeline only sees this object."""

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from irerero.config import PROVISIONAL, RAW, SAME_SITE_M
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

COMBINED = "openstreetmap+mineduc"  # the source of a network that holds both school lists


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
    """The schools for the distance layer: OpenStreetMap schools (with roads) and the MINEDUC
    school list together when both are loaded, a MINEDUC school within SAME_SITE_M of an OSM
    school counted once; otherwise whichever one is loaded; otherwise the simulated stand-in.
    Both lists are partial (OSM does not say which schools have pre-primary, MINEDUC's lists
    standalone pre-primary schools only), so any layer built on the MINEDUC list is labelled
    provisional. A school file with no usable point falls back, and its report says why."""
    listed = schools.load(raw)
    if osm.DATASET.present(raw):
        network = osm.load(raw)
        if listed is not None and listed[1].loaded:
            return combine(network, *listed)
        if listed is not None:
            network.report = listed[1].as_dict()
        return network
    if listed is None:
        return osm.load(raw)
    frame, report = listed
    if report.loaded:
        return osm.Network(schools=frame, status=PROVISIONAL, real=True, source=schools.SOURCE,
                           report=report.as_dict())  # fmt: skip
    fallback = osm.load(raw)
    fallback.report = report.as_dict()
    return fallback


def combine(network: osm.Network, listed: pd.DataFrame, report: schools.Report) -> osm.Network:
    """OSM schools plus the MINEDUC schools that are not at an OSM school's site."""
    from scipy.spatial import cKDTree

    from irerero.plan.distance import _metric

    mapped = network.schools.assign(origin="openstreetmap")
    listed = listed.assign(origin="mineduc")
    if len(mapped):
        osm_xy = _metric(mapped.lon.to_numpy(float), mapped.lat.to_numpy(float))
        list_xy = _metric(listed.lon.to_numpy(float), listed.lat.to_numpy(float))
        same = cKDTree(osm_xy).query(list_xy, distance_upper_bound=SAME_SITE_M)[0] <= SAME_SITE_M
    else:
        same = np.zeros(len(listed), dtype=bool)
    network.schools = pd.concat([mapped, listed[~same]], ignore_index=True)
    network.status, network.source = PROVISIONAL, COMBINED
    network.report = {
        **report.as_dict(),
        "osm_points": len(mapped),
        "mineduc_points": len(listed),
        "mineduc_same_site": int(same.sum()),
    }
    return network


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
