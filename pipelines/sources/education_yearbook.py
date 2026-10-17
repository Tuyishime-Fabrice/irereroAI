from irerero_contract.enums import Origin
from pipelines.sources.area_tables import AreaTableLoader, Direct
from pipelines.sources.spec import ADMIN_COLUMNS, Column, Dataset, ExpectedFile


class EducationYearbook(AreaTableLoader):
    dataset = Dataset(
        key="education_yearbook",
        title="Education Statistical Yearbook 2024/25",
        publisher="Ministry of Education (MINEDUC)",
        access="Public PDF; copy the pre-primary district table into the CSV",
        url="https://www.mineduc.gov.rw",
        licence="Published report; cite MINEDUC",
        origin=Origin.OFFICIAL,
        reference_year=2025,
        files=(
            ExpectedFile(
                "education_yearbook_2024_25_districts.csv",
                "csv",
                "Pre-primary enrolment by district typed from the yearbook",
            ),
        ),
        columns=(
            *ADMIN_COLUMNS,
            Column("pre_primary_enrolment", "integer", "Children enrolled in pre-primary"),
            Column(
                "pre_primary_ger",
                "number",
                "Gross enrolment ratio as a share; it can exceed 1",
                required=False,
            ),
            Column("pre_primary_schools", "integer", "Schools with pre-primary", required=False),
        ),
        level="district",
        joins_on="admin_code (or admin_name) at district level",
        used_by=("national overview", "need map: school readiness context"),
        produces=("area_indicator: pre_primary_enrolment, pre_primary_ger, ecd_centres",),
        fallback="Not shown until loaded",
        optional=True,
    )
    values = (
        Direct("pre_primary_enrolment", "pre_primary_enrolment"),
        Direct("pre_primary_ger", "pre_primary_ger"),
        Direct("ecd_centres", "pre_primary_schools"),
    )
