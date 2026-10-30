"""Share of young children more than 1 km from a school with pre-primary.

Children: WorldPop under-5 pixels inside each sector, or, while WorldPop is missing, points
spread evenly on a 250 m grid (labelled). Schools: OSM schools and kindergartens, plus NCDA
centres when an extract is loaded.

Distance: walking distance along the OSM road network where roads reach most of the sector's
children; otherwise straight-line distance, labelled "indicative" because it understates the
walk.
"""

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import points

from irerero.config import (
    GRID_SPACING_M,
    METRIC_CRS,
    MIN_ROAD_COVERAGE,
    SNAP_LIMIT_M,
    WALKING_DISTANCE_KM,
)
from irerero.data.sources import worldpop
from irerero.data.sources.osm import Network

ROAD = "road network"
STRAIGHT = "straight line (indicative)"
LIMIT_M = WALKING_DISTANCE_KM.value * 1000


@dataclass
class Children:
    xy: np.ndarray  # metric coordinates, n x 2
    weight: np.ndarray
    spread: str  # "WorldPop pixels" or "even grid"


def _metric(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    frame = gpd.GeoSeries(points(lon, lat), crs=4326).to_crs(METRIC_CRS)
    return np.column_stack([frame.x.to_numpy(), frame.y.to_numpy()])


def _grid(geometry_m: object) -> np.ndarray:
    minx, miny, maxx, maxy = geometry_m.bounds  # type: ignore[attr-defined]
    xs = np.arange(minx + GRID_SPACING_M / 2, maxx, GRID_SPACING_M)
    ys = np.arange(miny + GRID_SPACING_M / 2, maxy, GRID_SPACING_M)
    gx, gy = np.meshgrid(xs, ys)
    candidates = points(gx.ravel(), gy.ravel())
    inside = gpd.GeoSeries(candidates).within(geometry_m).to_numpy()
    xy = np.column_stack([gx.ravel(), gy.ravel()])[inside]
    if len(xy) == 0:  # a sector smaller than one grid cell
        c = geometry_m.representative_point()  # type: ignore[attr-defined]
        xy = np.array([[c.x, c.y]])
    return xy


def children(sectors: gpd.GeoDataFrame, raw: object) -> dict[str, Children]:
    metric = sectors.to_crs(METRIC_CRS)
    out = {}
    for geo_id, geometry, geometry_m in zip(
        sectors.geo_id, sectors.geometry, metric.geometry, strict=True
    ):
        pixels = worldpop.pixels(geometry, raw) if worldpop.DATASET.present(raw) else None  # type: ignore[arg-type]
        if pixels is not None and len(pixels):
            xy = _metric(pixels.lon.to_numpy(), pixels.lat.to_numpy())
            out[geo_id] = Children(xy, pixels.children.to_numpy(float), "WorldPop pixels")
        else:
            xy = _grid(geometry_m)
            out[geo_id] = Children(xy, np.ones(len(xy)), "even grid")
    return out


class RoadDistance:
    """Walking distance from any point to the nearest school, along the road network, up to
    the 1 km limit (and infinity beyond)."""

    def __init__(self, network: Network, schools_xy: np.ndarray):
        import networkx as nx
        from pyproj import Transformer

        ids, lon, lat, a, b = network.road_arrays()
        x, y = Transformer.from_crs(4326, METRIC_CRS, always_xy=True).transform(lon, lat)
        self.xy = np.column_stack([x, y])
        self.tree = cKDTree(self.xy)
        # Only roads near a school can lie on a walk of at most 1 km from it: every node of such
        # a walk is within 1 km of the school in a straight line. Leaving the others out of the
        # graph gives the same distances with a fraction of the memory (snapping still uses
        # every road node).
        near = cKDTree(schools_xy).query(self.xy, distance_upper_bound=LIMIT_M + 1)[0] <= LIMIT_M
        i, j = np.searchsorted(ids, a), np.searchsorted(ids, b)
        keep = near[i] & near[j]
        i, j = i[keep], j[keep]
        length = np.hypot(*(self.xy[i] - self.xy[j]).T)
        graph = nx.Graph()
        graph.add_weighted_edges_from(zip(i.tolist(), j.tolist(), length.tolist(), strict=True))
        # a virtual source joined to each school's nearest road node by the walk to the road
        snap, node = self.tree.query(schools_xy)
        source = -1
        for d, n in zip(snap, node, strict=True):
            if d <= SNAP_LIMIT_M:  # n is then within 500 m of the school, so kept as near
                old = graph.get_edge_data(source, n, {}).get("weight", np.inf)
                graph.add_edge(source, int(n), weight=min(float(d), old))
        self.reach = (
            nx.single_source_dijkstra_path_length(graph, source, cutoff=LIMIT_M, weight="weight")
            if source in graph
            else {}
        )

    def query(self, xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(distance in metres, near_road) for each point."""
        snap, node = self.tree.query(xy)
        along = np.array([self.reach.get(int(n), np.inf) for n in node])
        near = snap <= SNAP_LIMIT_M
        return np.where(near, snap + along, np.inf), near


def far_shares(
    sectors: gpd.GeoDataFrame,
    network: Network,
    raw: object,
    extra_schools: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Per sector: far_share (children beyond 1 km), distance_method, children_spread."""
    schools = network.schools[["lon", "lat"]]
    if extra_schools is not None and len(extra_schools):
        schools = pd.concat([schools, extra_schools[["lon", "lat"]]], ignore_index=True)
    schools_xy = _metric(schools.lon.to_numpy(float), schools.lat.to_numpy(float))
    straight = cKDTree(schools_xy)
    road = RoadDistance(network, schools_xy) if network.real and network.has_roads else None
    rows = []
    for geo_id, kids in children(sectors, raw).items():
        line, _ = straight.query(kids.xy)
        method, distance = STRAIGHT, line
        if road is not None:
            walk, near = road.query(kids.xy)
            if np.average(near, weights=kids.weight) >= MIN_ROAD_COVERAGE:
                method = ROAD
                # off-road points keep the straight line: no path is no evidence of no access
                distance = np.where(near, walk, line)
        far = float(np.average(distance > LIMIT_M, weights=kids.weight))
        rows.append(
            {
                "geo_id": geo_id,
                "far_share": round(far, 4),
                "distance_method": method,
                "children_spread": kids.spread,
            }
        )
    return pd.DataFrame(rows)
