from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class Rdhs2019Gps(PlannedAdapter):
    spec = AdapterSpec(
        name="rdhs_2019_gps",
        title="Rwanda DHS 2019-20 cluster locations",
        publisher="The DHS Program",
        reference_year=2020,
        origin=Origin.OFFICIAL,
        licence="DHS Program GPS dataset terms: separate request, no redistribution",
        url="https://dhsprogram.com",
        expected_files=(
            ExpectedFile("rdhs_2019_gps/*GE*/*", "Cluster point file (displaced coordinates)"),
            ExpectedFile("rdhs_2019_gps/*KR*.DTA", "Children's recode to join on cluster number"),
        ),
        target_tables=("area_indicator",),
        indicators=("stunting_prevalence_u5",),
        checks=(
            CheckSpec(
                "displacement_aware",
                "Clusters are assigned with their displacement buffer (urban 2 km, rural 5 km); "
                "a cluster whose buffer spans sectors is apportioned, never snapped",
            ),
            CheckSpec("cluster_join", "Every child record joins to one cluster location"),
            CheckSpec("missing_coordinates", "Clusters at 0,0 are dropped and counted"),
        ),
        notes="Feeds the spatial stunting-risk model in Phase 2. Never show cluster points.",
    )
