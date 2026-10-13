from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class Census2022(PlannedAdapter):
    spec = AdapterSpec(
        name="census_2022",
        title="Fifth Rwanda Population and Housing Census (PHC5), 2022",
        publisher="NISR",
        reference_year=2022,
        origin=Origin.OFFICIAL,
        licence="NISR microdata terms of use: no redistribution",
        url="https://microdata.statistics.gov.rw",
        expected_files=(
            ExpectedFile(
                "census_2022/*.dta", "Person-level microdata with sector of residence and age"
            ),
            ExpectedFile(
                "census_2022/sector_population_age_sex.csv",
                "Or, without microdata: published sector tables by single year of age and sex",
            ),
        ),
        target_tables=("area_indicator",),
        indicators=("population_0_2", "population_3_6"),
        checks=(
            CheckSpec("sector_match", "Every sector in the file maps to exactly one admin_unit"),
            CheckSpec("national_total", "National population equals the published PHC5 total"),
            CheckSpec("district_totals", "District totals equal the published district tables"),
            CheckSpec("non_negative", "No negative or missing counts"),
        ),
        notes=(
            "Sector counts are full-count values: write them with low and high left empty. "
            "They are the denominators the need model scales to."
        ),
    )
