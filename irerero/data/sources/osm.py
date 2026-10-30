"""OpenStreetMap Rwanda extract: schools and walkable roads for the distance layer."""

from array import array
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd

from irerero.config import DEMO, OBSERVED, RAW, SIMULATED
from irerero.data.spec import Column, Dataset
from irerero.data.validate import read_csv

PBF = "rwanda-latest.osm.pbf"
DATASET = Dataset(
    key="osm",
    title="OpenStreetMap Rwanda extract",
    publisher="OpenStreetMap contributors, via Geofabrik",
    files=(PBF,),
    format="OSM PBF",
    columns=(),
    level="points and road network",
    reference_period="extract date",
    licence="ODbL 1.0",
    url="https://download.geofabrik.de/africa/rwanda.html",
    used_by=("PLAN: share of children more than 1 km from a school with pre-primary",),
    status=OBSERVED,
    fallback="Simulated school points; straight-line distance, labelled indicative",
    notes=(
        "Schools are amenity=school or amenity=kindergarten. Most Rwandan primary schools host "
        "pre-primary, but OSM does not say which: treat the layer as an approximation.",
        "Needs `uv sync --extra osm` (pyosmium and networkx; on Streamlit, requirements.txt). "
        "Where roads reach fewer than half a sector's children, distance is straight-line and "
        "labelled indicative.",
        "Put the Geofabrik extract (any name ending .osm.pbf) through `make intake`: it keeps "
        "schools and walkable roads and stages rwanda-latest.osm.pbf. With the MINEDUC school "
        "list also staged, both are used, a MINEDUC school within 100 m of an OSM school counted "
        "once, and the distance stays provisional while the lists are partial.",
    ),
)
WALKABLE = {
    "footway", "path", "track", "steps", "pedestrian", "living_street", "residential",
    "unclassified", "service", "tertiary", "tertiary_link", "secondary", "secondary_link",
    "primary", "primary_link", "trunk", "trunk_link", "road",
}  # fmt: skip
SCHOOL_COLUMNS = (
    Column("school_id", "text", "Identifier"),
    Column("lon", "longitude", "Longitude (WGS84)"),
    Column("lat", "latitude", "Latitude (WGS84)"),
)


@dataclass
class Network:
    schools: pd.DataFrame
    nodes: dict[int, tuple[float, float]] = field(default_factory=dict)
    edges: list[tuple[int, int]] = field(default_factory=list)
    status: str = OBSERVED
    real: bool = True
    source: str = "osm"
    """osm, mineduc_provisional (a partial school list) or demo"""
    report: dict | None = None
    """The school loader's report (records, invalid coordinates, missing properties)."""
    roads: tuple[np.ndarray, ...] | None = None
    """(node ids, lon, lat, edge from, edge to) as arrays: the loader's compact form of `nodes`
    and `edges` (a whole country's road nodes do not fit in memory as Python objects)."""

    @property
    def has_roads(self) -> bool:
        return bool(self.edges) or (self.roads is not None and len(self.roads[3]) > 0)

    def road_arrays(self) -> tuple[np.ndarray, ...]:
        if self.roads is not None:
            return self.roads
        ids = np.sort(np.fromiter(self.nodes, dtype=np.int64, count=len(self.nodes)))
        lonlat = np.array([self.nodes[i] for i in ids], dtype=float).reshape(-1, 2)
        pairs = np.array(self.edges, dtype=np.int64).reshape(-1, 2)
        return ids, lonlat[:, 0], lonlat[:, 1], pairs[:, 0], pairs[:, 1]


def load(raw: Path = RAW) -> Network:
    if not DATASET.present(raw):
        schools = read_csv(DEMO / "osm" / "schools.csv", SCHOOL_COLUMNS)
        return Network(schools=schools, status=SIMULATED, real=False, source="demo")
    import osmium

    network = Network(schools=pd.DataFrame())
    schools: list[dict[str, object]] = []
    refs, lons, lats = array("q"), array("d"), array("d")  # every road node, once per way
    start, end = array("q"), array("q")

    class Handler(osmium.SimpleHandler):  # type: ignore[misc]
        def node(self, n: object) -> None:
            if n.tags.get("amenity") in ("school", "kindergarten") and n.location.valid():  # type: ignore[attr-defined]
                schools.append(
                    {"school_id": f"osm-{n.id}", "lon": n.location.lon, "lat": n.location.lat}  # type: ignore[attr-defined]
                )

        def way(self, w: object) -> None:
            tags = w.tags  # type: ignore[attr-defined]
            if tags.get("amenity") in ("school", "kindergarten"):
                nodes = [nd for nd in w.nodes if nd.location.valid()]  # type: ignore[attr-defined]
                if nodes:
                    schools.append(
                        {
                            "school_id": f"osm-w{w.id}",  # type: ignore[attr-defined]
                            "lon": sum(nd.location.lon for nd in nodes) / len(nodes),
                            "lat": sum(nd.location.lat for nd in nodes) / len(nodes),
                        }
                    )
            if tags.get("highway") not in WALKABLE or tags.get("access") == "private":
                return
            way = [nd for nd in w.nodes if nd.location.valid()]  # type: ignore[attr-defined]
            for nd in way:
                refs.append(nd.ref)
                lons.append(nd.location.lon)
                lats.append(nd.location.lat)
            for a, b in pairwise(way):
                start.append(a.ref)
                end.append(b.ref)

    Handler().apply_file(str(DATASET.folder(raw) / PBF), locations=True)
    network.schools = pd.DataFrame(schools, columns=["school_id", "lon", "lat"])
    ids, first = np.unique(np.frombuffer(refs, dtype=np.int64), return_index=True)
    network.roads = (
        ids,
        np.frombuffer(lons, dtype=float)[first],
        np.frombuffer(lats, dtype=float)[first],
        np.frombuffer(start, dtype=np.int64).copy(),
        np.frombuffer(end, dtype=np.int64).copy(),
    )
    return network
