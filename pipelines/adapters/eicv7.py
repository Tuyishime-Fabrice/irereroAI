from irerero_contract.enums import Origin
from pipelines.adapter import AdapterSpec, CheckSpec, ExpectedFile, PlannedAdapter


class Eicv7(PlannedAdapter):
    spec = AdapterSpec(
        name="eicv7",
        title="Integrated Household Living Conditions Survey 7 (EICV7)",
        publisher="NISR",
        reference_year=None,
        origin=Origin.OFFICIAL,
        licence="NISR microdata terms of use: no redistribution",
        url="https://microdata.statistics.gov.rw",
        expected_files=(
            ExpectedFile(
                "eicv7/*household*.dta", "Household file with weight, cluster and stratum"
            ),
            ExpectedFile("eicv7/*person*.dta", "Person file with age, sex and activity"),
        ),
        target_tables=("area_indicator",),
        indicators=("poverty_headcount",),
        checks=(
            CheckSpec("design_variables", "Weight, cluster and stratum present on every record"),
            CheckSpec("published_poverty", "District poverty rates reproduce the published report"),
            CheckSpec("sample_size", "Each district estimate carries its unweighted sample size"),
        ),
        notes=(
            "EICV is representative at district level. Write district estimates with design-based "
            "intervals and sample_size; sector values come from the Phase 2 small-area model, not "
            "from this adapter. Set reference_year from the release."
        ),
    )
