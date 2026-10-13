from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class Boundaries(PlannedAdapter):
    spec = AdapterSpec(
        name="boundaries",
        title="Official administrative boundaries, province to village",
        publisher="NISR",
        reference_year=None,
        origin=Origin.OFFICIAL,
        licence="NISR open data terms",
        url="https://www.statistics.gov.rw",
        expected_files=(
            ExpectedFile("boundaries/*.geojson", "Boundaries per level with official codes"),
        ),
        target_tables=("admin_unit",),
        checks=(
            CheckSpec("unit_counts", "Unit counts per level match NISR's published counts"),
            CheckSpec(
                "code_crosswalk",
                "Every existing district and sector code gets a nisr_code; unmatched names go to "
                "a manual review list instead of being guessed",
            ),
            CheckSpec("valid_geometry", "Geometries are valid and nest inside their parent"),
        ),
        notes=(
            "Phase 1 loads district and sector shapes from geoBoundaries (CC BY 4.0, sourced from "
            "NISR open data) in pipelines/demo/geography.py. This adapter adds official codes, "
            "cells and villages, and keeps existing codes stable."
        ),
    )
