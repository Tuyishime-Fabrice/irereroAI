"""Indicator codes allowed in area_indicator.indicator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Indicator:
    code: str
    unit: str
    description: str


INDICATORS: dict[str, Indicator] = {
    i.code: i
    for i in (
        Indicator("population_0_2", "count", "Children aged 0 to 2"),
        Indicator("population_3_6", "count", "Children aged 3 to 6"),
        Indicator("stunting_prevalence_u5", "share", "Children under 5 below -2 SD height-for-age"),
        Indicator("poverty_headcount", "share", "Share of people below the national poverty line"),
        Indicator("pre_primary_ger", "share", "Pre-primary gross enrolment ratio"),
        Indicator("women_lfp_rate", "share", "Labour force participation rate, women 16+"),
        Indicator(
            "mothers_childcare_barrier_share",
            "share",
            "Mothers of under-3s outside work who give childcare as the reason",
        ),
        Indicator("ecd_centres", "count", "ECD centres registered in the area"),
        Indicator(
            "travel_minutes_to_ecd_median",
            "minutes",
            "Median walking time from a home to the nearest ECD centre",
        ),
    )
}
