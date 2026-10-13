from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class NcdaMapping(PlannedAdapter):
    spec = AdapterSpec(
        name="ncda_mapping",
        title="NCDA ECD Mapping System and digitised ECD book",
        publisher="National Child Development Agency (NCDA)",
        reference_year=None,
        origin=Origin.PARTNER,
        licence="Data sharing agreement with NCDA",
        url=None,
        expected_files=(
            ExpectedFile("ncda_mapping/centres.csv", "Centre register export with NCDA ids"),
            ExpectedFile("ncda_mapping/ecd_book_*.csv", "Digitised weekly ECD book entries"),
        ),
        target_tables=("centre", "weekly_report"),
        checks=(
            CheckSpec("ncda_ref_unique", "NCDA ids are unique and stored in centre.ncda_ref"),
            CheckSpec("point_in_sector", "Each centre point falls in its declared sector"),
            CheckSpec("near_duplicates", "Centres within 50 m with similar names are listed"),
            CheckSpec(
                "report_rules",
                "Book entries pass irerero_contract.validation; flagged rows keep their flags",
            ),
            CheckSpec("no_child_data", "No column holds child names, photos or ids"),
        ),
        notes=(
            "IrereroAI is a layer on the NCDA system: match on ncda_ref first, then on location "
            "and name, and never overwrite a verification done in IrereroAI."
        ),
    )
