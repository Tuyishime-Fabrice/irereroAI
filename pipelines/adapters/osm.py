from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class Osm(PlannedAdapter):
    spec = AdapterSpec(
        name="osm",
        title="OpenStreetMap Rwanda extract",
        publisher="OpenStreetMap contributors (via Geofabrik)",
        reference_year=None,
        origin=Origin.PUBLIC,
        licence="ODbL 1.0",
        url="https://download.geofabrik.de/africa/rwanda.html",
        expected_files=(ExpectedFile("osm/rwanda-latest.osm.pbf", "Roads, paths and places"),),
        target_tables=("area_indicator", "candidate_site"),
        indicators=("travel_minutes_to_ecd_median",),
        checks=(
            CheckSpec(
                "network_connected", "The walkable network's main component covers 95% of edges"
            ),
            CheckSpec("centre_snapping", "Every centre snaps to the network within 500 m"),
            CheckSpec("extract_date", "The extract date is recorded as the reference date"),
        ),
        notes=(
            "Replaces the straight-line catchment in CoverageModel with walking time. "
            "place=village nodes add village candidate sites."
        ),
    )
