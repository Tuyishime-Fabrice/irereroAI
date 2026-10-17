"""OpenStreetMap Rwanda extract: schools and walkable roads for the distance layer."""

from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

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
        "Needs `uv sync --extra osm` (pyosmium and networkx). Without it, or where roads are "
        "thin, distance is straight-line and labelled indicative.",
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


def load(raw: Path = RAW) -> Network:
    if not DATASET.present(raw):
        schools = read_csv(DEMO / "osm" / "schools.csv", SCHOOL_COLUMNS)
        return Network(schools=schools, status=SIMULATED, real=False)
    import osmium

    network = Network(schools=pd.DataFrame())
    schools: list[dict[str, object]] = []

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
            refs = [(nd.ref, nd.location) for nd in w.nodes if nd.location.valid()]  # type: ignore[attr-defined]
            for ref, loc in refs:
                network.nodes[ref] = (loc.lon, loc.lat)
            network.edges.extend((a, b) for (a, _), (b, _) in pairwise(refs))

    Handler().apply_file(str(DATASET.folder(raw) / PBF), locations=True)
    network.schools = pd.DataFrame(schools, columns=["school_id", "lon", "lat"])
    return network
