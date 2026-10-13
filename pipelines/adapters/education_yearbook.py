from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class EducationYearbook(PlannedAdapter):
    spec = AdapterSpec(
        name="education_yearbook",
        title="Education Statistical Yearbook",
        publisher="MINEDUC",
        reference_year=None,
        origin=Origin.OFFICIAL,
        licence="Published statistics; confirm terms for the school list",
        url="https://www.mineduc.gov.rw",
        expected_files=(
            ExpectedFile("education_yearbook/pre_primary_by_district.csv", "Enrolment and GER"),
            ExpectedFile("education_yearbook/schools.csv", "School list with code and location"),
        ),
        target_tables=("area_indicator", "candidate_site"),
        indicators=("pre_primary_ger",),
        checks=(
            CheckSpec("published_ger", "District GER matches the yearbook tables"),
            CheckSpec("school_codes_unique", "School codes are unique"),
            CheckSpec("points_in_sector", "Each school point falls in its declared sector"),
        ),
        notes="Schools become candidate_site rows of kind 'school' for school-based ECD.",
    )
