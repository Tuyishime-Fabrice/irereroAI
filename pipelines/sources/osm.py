"""OpenStreetMap: walkable ways for walking-time catchments, and facility points.

pyosmium is imported only when the extract is present (`uv sync --extra geo`).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from irerero_contract.enums import FacilityKind, Origin
from irerero_engine.travel import RoadNetwork
from irerero_engine.types import Position
from pipelines.config import PILOT_DISTRICTS
from pipelines.runs import CheckResult
from pipelines.sources.base import Loader, LoadReport
from pipelines.sources.facilities import write_facilities
from pipelines.sources.readers import SchemaError
from pipelines.sources.spec import Dataset, ExpectedFile

FILE = "rwanda-latest.osm.pbf"
WALKABLE = {
    "footway", "path", "track", "steps", "pedestrian", "living_street", "residential",
    "unclassified", "service", "tertiary", "tertiary_link", "secondary", "secondary_link",
    "primary", "primary_link", "trunk", "trunk_link", "road",
}  # fmt: skip
# Search a little beyond the district so catchments near its edge use the roads across it.
MARGIN_DEGREES = 0.05
BBOX = text(
    "SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM ("
    "SELECT ST_Extent(geom) AS e FROM admin_unit WHERE code = ANY(:districts)) x"
)


def facility_kind(tags: Any) -> FacilityKind | None:
    amenity = tags.get("amenity")
    if amenity == "school":
        return FacilityKind.SCHOOL
    if amenity in ("kindergarten", "childcare"):
        return FacilityKind.CHILDCARE
    if amenity in ("hospital", "clinic", "doctors") or tags.get("healthcare"):
        return FacilityKind.HEALTH
    return None


@dataclass
class Extract:
    nodes: dict[int, tuple[float, float]] = field(default_factory=dict)
    edges: list[tuple[int, int]] = field(default_factory=list)
    facilities: list[dict[str, Any]] = field(default_factory=list)


def read_extract(path: Path, bbox: tuple[float, float, float, float]) -> Extract:
    try:
        import osmium
    except ImportError as error:
        raise SchemaError(
            "The OpenStreetMap extract needs the geo extras: run `uv sync --extra geo`"
        ) from error
    west, south, east, north = bbox
    extract = Extract()

    def inside(lon: float, lat: float) -> bool:
        return west <= lon <= east and south <= lat <= north

    class Handler(osmium.SimpleHandler):  # type: ignore[misc]
        def node(self, n: Any) -> None:
            kind = facility_kind(n.tags)
            if kind and n.location.valid() and inside(n.location.lon, n.location.lat):
                extract.facilities.append(
                    {
                        "id": f"osm-n{n.id}",
                        "kind": kind,
                        "name": n.tags.get("name"),
                        "lon": n.location.lon,
                        "lat": n.location.lat,
                    }
                )

        def way(self, w: Any) -> None:
            if w.tags.get("highway") not in WALKABLE or w.tags.get("access") == "private":
                return
            refs = [(nd.ref, nd.location) for nd in w.nodes if nd.location.valid()]
            if not any(inside(loc.lon, loc.lat) for _, loc in refs):
                return
            for ref, loc in refs:
                extract.nodes[ref] = (loc.lon, loc.lat)
            extract.edges += [(a, b) for (a, _), (b, _) in pairwise(refs)]

    try:
        Handler().apply_file(str(path), locations=True)
    except RuntimeError as error:
        raise SchemaError(f"{path.name}: not a readable OSM PBF file ({error})") from error
    if not extract.edges:
        raise SchemaError(f"{path.name}: no walkable ways inside the pilot district")
    return extract


def pilot_bbox(conn: Connection, districts: Sequence[str]) -> tuple[float, float, float, float]:
    west, south, east, north = conn.execute(BBOX, {"districts": list(districts)}).one()
    return (
        west - MARGIN_DEGREES,
        south - MARGIN_DEGREES,
        east + MARGIN_DEGREES,
        north + MARGIN_DEGREES,
    )


def road_network(conn: Connection, extract: Extract, metres_per_minute: float) -> RoadNetwork:
    """Projects the nodes to EPSG:32735 in PostGIS and builds the walking graph."""
    conn.execute(text("CREATE TEMP TABLE osm_node (id bigint, lon float, lat float)"))
    conn.execute(
        text("INSERT INTO osm_node VALUES (:id, :lon, :lat)"),
        [{"id": k, "lon": lon, "lat": lat} for k, (lon, lat) in extract.nodes.items()],
    )
    nodes = {
        row.id: Position(row.x, row.y)
        for row in conn.execute(
            text(
                "SELECT id, ST_X(p) AS x, ST_Y(p) AS y FROM (SELECT id, ST_Transform("
                "ST_SetSRID(ST_MakePoint(lon, lat), 4326), 32735) AS p FROM osm_node) n"
            )
        )
    }
    conn.execute(text("DROP TABLE osm_node"))
    return RoadNetwork(nodes, extract.edges, metres_per_minute)


class Osm(Loader):
    dataset = Dataset(
        key="osm",
        title="OpenStreetMap Rwanda extract",
        publisher="OpenStreetMap contributors, via Geofabrik",
        access="Open download",
        url="https://download.geofabrik.de/africa/rwanda.html",
        licence="ODbL 1.0",
        origin=Origin.PUBLIC,
        reference_year=None,
        files=(ExpectedFile(FILE, "osm.pbf", "The whole-country extract from Geofabrik"),),
        columns=(),
        level="road network",
        joins_on="Ways and points inside the pilot district, plus a 5 km margin",
        used_by=(
            "catchments: walking time along roads and paths",
            "need map: school, childcare and health facility points",
        ),
        produces=("catchment (walking minutes)", "facility: school, childcare, health"),
        fallback=(
            "Walking time estimated from straight-line distance x 1.3 at 4 km/h; no facility points"
        ),
        notes=(
            "Walkable ways: footways, paths, tracks and roads, except private ones. Each place "
            "walks in a straight line (x 1.3) to its nearest way.",
        ),
    )

    def load(self, conn: Connection, folder: Path, run_id: uuid.UUID) -> LoadReport:
        """Writes facility points. The road network is read again by the catchment step."""
        extract = read_extract(folder / FILE, pilot_bbox(conn, PILOT_DISTRICTS))
        written = write_facilities(conn, self.dataset, run_id, extract.facilities)
        return LoadReport(
            {"facility": written},
            [
                CheckResult("walkable_ways", True, f"{len(extract.edges)} way segments"),
                CheckResult("facilities", True, f"{written} schools, childcare and health points"),
            ],
        )
