from irerero_contract.enums import Origin
from pipelines.sources.area_tables import AreaTableLoader, Direct
from pipelines.sources.base import interval_columns
from pipelines.sources.spec import ADMIN_COLUMNS, INTERVAL_NOTE, Column, Dataset, ExpectedFile


class Lfs2025(AreaTableLoader):
    dataset = Dataset(
        key="lfs_2025",
        title="Labour Force Survey 2025",
        publisher="NISR",
        access="Free registration on the NISR microdata portal",
        url="https://microdata.statistics.gov.rw",
        licence="NISR microdata terms of use: no redistribution",
        origin=Origin.OFFICIAL,
        reference_year=2025,
        files=(ExpectedFile("lfs_2025_districts.csv", "csv", "One row per district"),),
        columns=ADMIN_COLUMNS
        + interval_columns(
            "women_lfp_rate_mothers_u3",
            "Labour force participation of women with a child under 3",
        )
        + interval_columns(
            "mothers_childcare_barrier_share",
            "Mothers of under-3s outside work who give childcare as the reason",
            required=False,
        )
        + (Column("sample_size", "integer", "Women in the sample", required=False),),
        level="district",
        joins_on="admin_code (or admin_name) at district level; province rows are also accepted",
        used_by=("need model: mothers' childcare barrier", "optimizer: mothers' employment weight"),
        produces=("area_indicator: women_lfp_rate_mothers_u3, mothers_childcare_barrier_share",),
        fallback="Simulated childcare-barrier share per sector, labelled simulated",
        notes=(INTERVAL_NOTE,),
    )
    values = (
        Direct("women_lfp_rate_mothers_u3", "women_lfp_rate_mothers_u3"),
        Direct("mothers_childcare_barrier_share", "mothers_childcare_barrier_share"),
    )
