from irerero_contract.enums import Origin
from pipelines.sources.area_tables import AreaTableLoader, Direct, Ratio
from pipelines.sources.spec import ADMIN_COLUMNS, Column, Dataset, ExpectedFile


class Census2022(AreaTableLoader):
    dataset = Dataset(
        key="census_2022",
        title="Fifth Rwanda Population and Housing Census (PHC5), 2022",
        publisher="NISR",
        access="Free registration on the NISR microdata portal; district tables are published",
        url="https://microdata.statistics.gov.rw",
        licence="NISR microdata terms of use: no redistribution",
        origin=Origin.OFFICIAL,
        reference_year=2022,
        files=(
            ExpectedFile(
                "census_2022_areas.csv",
                "csv",
                "One row per area, aggregated from the microdata or the published tables",
            ),
        ),
        columns=(
            *ADMIN_COLUMNS,
            Column("children_0_2", "integer", "Children aged 0 to 2, girls and boys"),
            Column("children_3_6", "integer", "Children aged 3 to 6, girls and boys"),
            Column("households", "integer", "Private households", required=False),
            Column(
                "households_improved_water",
                "integer",
                "Households whose main drinking water source is improved",
                required=False,
            ),
            Column(
                "households_improved_sanitation",
                "integer",
                "Households with improved sanitation",
                required=False,
            ),
            Column("mothers_u6", "integer", "Mothers of a child under 6", required=False),
            Column(
                "mothers_u6_secondary",
                "integer",
                "Of them, with secondary education or more",
                required=False,
            ),
            Column("mothers_u6_employed", "integer", "Of them, employed", required=False),
        ),
        level="sector",
        joins_on="admin_code (or admin_name) at sector level; district rows are also accepted",
        used_by=("need model: children per sector", "need map", "optimizer (via need)"),
        produces=(
            "area_indicator: population_0_2, population_3_6, households_improved_water_share, "
            "households_improved_sanitation_share, mothers_secondary_share, "
            "mothers_employed_share",
        ),
        fallback="Simulated child counts per sector from the demo generator, labelled simulated",
        notes=(
            "Sector rows replace the simulated child counts in the pilot district. Girls and "
            "boys are summed; the planner does not use the split.",
        ),
    )
    values = (
        Direct("population_0_2", "children_0_2"),
        Direct("population_3_6", "children_3_6"),
        Ratio("households_improved_water_share", "households_improved_water", "households"),
        Ratio(
            "households_improved_sanitation_share", "households_improved_sanitation", "households"
        ),
        Ratio("mothers_secondary_share", "mothers_u6_secondary", "mothers_u6"),
        Ratio("mothers_employed_share", "mothers_u6_employed", "mothers_u6"),
    )
