"""Every input value as one observation row: where it is, what it is, when, from which source
(and page), and its status."""

import pandas as pd

from irerero.config import PUBLISHED
from irerero.data.sources import census, eicv, projections, rdhs, worldpop
from irerero.data.sources import yearbook as yearbook_source
from irerero.data.sources.base import Loaded
from irerero.pipeline.inputs import Inputs

COLUMNS = [
    "geo_id",
    "indicator_id",
    "value",
    "reference_period",
    "source_id",
    "source_page",
    "status",
    "qa_flag",
]
CENSUS = {
    "children_3_5": "children_3_5",
    "children_3_5_attending": "attending_3_5",
    "children_3_5_never_attended": "never_attended_3_5",
    "population": "population",
    "children_0_4": "children_0_4",
    "households": "households",
    "hh_improved_water": "hh_improved_water",
    "hh_improved_sanitation": "hh_improved_sanitation",
    "hh_electricity": "hh_electricity",
    "urban_share": "urban_share",
    "women_secondary_share": "women_secondary_share",
}
YEARBOOK = {
    "pupils": "pp_pupils",
    "schools": "pp_schools",
    "classrooms": "pp_classrooms",
    "teachers": "pp_teachers",
    "qualified_teachers": "pp_teachers_qualified",
}


def _melt(
    loaded: Loaded, source_id: str, columns: dict[str, str], period: str | pd.Series
) -> pd.DataFrame:
    frame = loaded.frame
    parts = []
    for column, indicator in columns.items():
        if column not in frame or frame[column].isna().all():
            continue
        part = pd.DataFrame(
            {
                "geo_id": frame.geo_id,
                "indicator_id": indicator,
                "value": frame[column].astype(float),
                "reference_period": period,
                "source_id": source_id,
                "source_page": frame.get("source_page"),
                "status": loaded.status,
                "qa_flag": None,
            }
        )
        parts.append(part.dropna(subset=["value"]))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=COLUMNS)


def build_observations(inputs: Inputs) -> pd.DataFrame:
    frames = [
        _melt(inputs.census_sectors, census.DATASET.key, CENSUS, "2022"),
        _melt(inputs.census_districts, census.DATASET.key, CENSUS, "2022"),
        _melt(
            inputs.projections,
            projections.DATASET.key,
            {
                "population": "population_projected",
                "population_low": "population_projected_low",
                "population_high": "population_projected_high",
            },
            inputs.projections.frame.year.astype(str),
        ),
        _melt(
            inputs.yearbook,
            yearbook_source.DATASET.key,
            YEARBOOK,
            inputs.yearbook.frame.school_year,
        ),
        _melt(
            inputs.stunting,
            rdhs.DATASET.key,
            {
                "stunting_u5": "stunting_u5",
                "stunting_u5_low": "stunting_u5_low",
                "stunting_u5_high": "stunting_u5_high",
            },
            "2025",
        ),
        _melt(inputs.poverty, eicv.DATASET.key, {"poverty_rate": "poverty_rate"}, "2023/24"),
    ]
    if inputs.under5 is not None:
        frames.append(
            pd.DataFrame(
                {
                    "geo_id": inputs.under5.index,
                    "indicator_id": "under5_worldpop",
                    "value": inputs.under5.to_numpy(),
                    "reference_period": "2020",
                    "source_id": worldpop.DATASET.key,
                    "source_page": None,
                    "status": PUBLISHED,
                    "qa_flag": None,
                }
            )
        )
    out = pd.concat(frames, ignore_index=True)[COLUMNS]
    return out
