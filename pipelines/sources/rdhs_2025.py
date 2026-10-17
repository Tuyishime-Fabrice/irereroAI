from irerero_contract.enums import Origin
from pipelines.sources.area_tables import AreaTableLoader, Direct
from pipelines.sources.base import interval_columns
from pipelines.sources.spec import ADMIN_COLUMNS, INTERVAL_NOTE, Column, Dataset, ExpectedFile


class Rdhs2025(AreaTableLoader):
    dataset = Dataset(
        key="rdhs_2025",
        title="Rwanda Demographic and Health Survey 2025, Key Indicators Report",
        publisher="NISR, Ministry of Health and The DHS Program",
        access="Public PDF from NISR; copy the district stunting table into the CSV",
        url="https://www.statistics.gov.rw",
        licence="Published report; cite NISR and The DHS Program",
        origin=Origin.OFFICIAL,
        reference_year=2025,
        files=(
            ExpectedFile(
                "rdhs_2025_key_indicators.csv",
                "csv",
                "District stunting table typed from the Key Indicators Report",
            ),
        ),
        columns=ADMIN_COLUMNS
        + interval_columns("stunting_u5", "Children under 5 below -2 SD height-for-age")
        + (Column("sample_size", "integer", "Children measured", required=False),),
        level="district",
        joins_on="admin_code (or admin_name) at district level",
        used_by=("need model: stunting risk", "need map", "optimizer: stunting weight"),
        produces=("area_indicator: stunting_prevalence_u5",),
        fallback=(
            "Simulated sector stunting risk around the published Gicumbi value (38.8%), "
            "labelled simulated"
        ),
        notes=(
            INTERVAL_NOTE,
            "Values are shares: write 38.8% as 0.388.",
        ),
    )
    values = (Direct("stunting_prevalence_u5", "stunting_u5"),)
