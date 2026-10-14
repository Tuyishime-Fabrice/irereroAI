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
            ExpectedFile(
                "ncda_mapping/centres.csv",
                "Centre register export with NCDA ids, capacity and latest enrolment",
            ),
        ),
        target_tables=("centre",),
        checks=(
            CheckSpec("ncda_ref_unique", "NCDA ids are unique and stored in centre.ncda_ref"),
            CheckSpec("point_in_sector", "Each centre point falls in its declared sector"),
            CheckSpec("near_duplicates", "Centres within 50 m with similar names are listed"),
            CheckSpec("enrolment_plausible", "Enrolment is between 0 and three times capacity"),
            CheckSpec("no_child_data", "No column holds child names, photos or ids"),
        ),
        notes=(
            "IrereroAI is a planning layer on the NCDA system: it reads centres, never edits them. "
            "Match on ncda_ref first, then on location and name."
        ),
    )
