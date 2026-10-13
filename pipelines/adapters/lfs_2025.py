from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class Lfs2025(PlannedAdapter):
    spec = AdapterSpec(
        name="lfs_2025",
        title="Labour Force Survey 2025",
        publisher="NISR",
        reference_year=2025,
        origin=Origin.OFFICIAL,
        licence="NISR microdata terms of use: no redistribution",
        url="https://microdata.statistics.gov.rw",
        expected_files=(
            ExpectedFile("lfs_2025/*.dta", "Person-level file with activity status and reasons"),
        ),
        target_tables=("area_indicator",),
        indicators=("women_lfp_rate", "mothers_childcare_barrier_share"),
        checks=(
            CheckSpec("published_rates", "National and district rates reproduce the LFS report"),
            CheckSpec(
                "barrier_definition",
                "Barrier share counts mothers of under-3s outside work who give childcare or "
                "family duties as the reason; the variable mapping is recorded in the run",
            ),
            CheckSpec("sample_size", "Each estimate carries its unweighted sample size"),
        ),
    )
