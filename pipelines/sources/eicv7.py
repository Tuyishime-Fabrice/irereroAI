from irerero_contract.enums import Origin
from pipelines.sources.area_tables import AreaTableLoader, Direct
from pipelines.sources.base import interval_columns
from pipelines.sources.spec import ADMIN_COLUMNS, INTERVAL_NOTE, Column, Dataset, ExpectedFile


class Eicv7(AreaTableLoader):
    dataset = Dataset(
        key="eicv7",
        title="Integrated Household Living Conditions Survey 7 (EICV7), 2023/24",
        publisher="NISR",
        access="Free registration on the NISR microdata portal",
        url="https://microdata.statistics.gov.rw",
        licence="NISR microdata terms of use: no redistribution",
        origin=Origin.OFFICIAL,
        reference_year=2024,
        files=(ExpectedFile("eicv7_districts.csv", "csv", "One row per district"),),
        columns=ADMIN_COLUMNS
        + interval_columns("poverty_headcount", "Share of people below the poverty line")
        + interval_columns(
            "pre_primary_attendance_rate",
            "Share of children aged 3 to 6 attending pre-primary",
            required=False,
        )
        + (
            Column(
                "minutes_to_pre_primary_median",
                "number",
                "Median minutes to the nearest pre-primary school, as reported",
                required=False,
            ),
            Column("sample_size", "integer", "Households interviewed", required=False),
        ),
        level="district",
        joins_on="admin_code (or admin_name) at district level",
        used_by=("need map: poverty in sector details", "national overview"),
        produces=(
            "area_indicator: poverty_headcount, pre_primary_attendance_rate, "
            "travel_minutes_to_ecd_median",
        ),
        fallback="Simulated poverty share per sector; the other values are not shown",
        notes=(INTERVAL_NOTE,),
    )
    values = (
        Direct("poverty_headcount", "poverty_headcount"),
        Direct("pre_primary_attendance_rate", "pre_primary_attendance_rate"),
        Direct("travel_minutes_to_ecd_median", "minutes_to_pre_primary_median"),
    )
