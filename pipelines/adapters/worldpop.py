from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class WorldPop(PlannedAdapter):
    spec = AdapterSpec(
        name="worldpop",
        title="WorldPop age and sex structures, constrained, 100 m",
        publisher="WorldPop, University of Southampton",
        reference_year=None,
        origin=Origin.PUBLIC,
        licence="CC BY 4.0",
        url="https://www.worldpop.org",
        expected_files=(
            ExpectedFile("worldpop/rwa_[fm]_0_*.tif", "Population under 1, by sex"),
            ExpectedFile("worldpop/rwa_[fm]_1_*.tif", "Population aged 1 to 4, by sex"),
            ExpectedFile("worldpop/rwa_[fm]_5_*.tif", "Population aged 5 to 9, by sex"),
        ),
        target_tables=("area_indicator",),
        indicators=("population_0_2", "population_3_6"),
        checks=(
            CheckSpec("crs", "Rasters are EPSG:4326 with the expected grid"),
            CheckSpec("census_consistency", "Sector sums are within the agreed tolerance of PHC5"),
            CheckSpec("nodata", "Nodata cells are excluded, not counted as zero people"),
        ),
        notes=(
            "Age bands are 0, 1-4 and 5-9: split into 0-2 and 3-6 with census single-year shares. "
            "Also used to place village candidate sites at population centres."
        ),
    )
