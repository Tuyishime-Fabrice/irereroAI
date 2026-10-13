from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class Rdhs2025(PlannedAdapter):
    spec = AdapterSpec(
        name="rdhs_2025",
        title="Rwanda Demographic and Health Survey 2025",
        publisher="NISR, Ministry of Health and The DHS Program",
        reference_year=2025,
        origin=Origin.OFFICIAL,
        licence="DHS Program dataset terms: registered users, no redistribution",
        url="https://dhsprogram.com",
        expected_files=(
            ExpectedFile("rdhs_2025/*KR*.DTA", "Children's recode with height-for-age and weights"),
        ),
        target_tables=("area_indicator",),
        indicators=("stunting_prevalence_u5",),
        checks=(
            CheckSpec(
                "flagged_measures", "Implausible height-for-age values excluded per DHS rules"
            ),
            CheckSpec(
                "published_stunting",
                "District stunting reproduces the published tables "
                "(Gicumbi 38.8% is the demo anchor)",
            ),
            CheckSpec("intervals", "Every district value has a design-based 95% interval"),
        ),
        notes=(
            "District-level direct estimates only. Sector stunting risk is a Phase 2 model output."
        ),
    )
