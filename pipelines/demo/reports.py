"""Twelve weeks of simulated weekly reports, with the planted problems the demo reveals.

Every generated report goes through the same validation as a real one, so the quality flags
on the implausible jump come from the production rules, not from the generator.
"""

import math
import random
from dataclasses import asdict
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import Connection, text

from irerero_contract.enums import CentreType, MainProblem, ReportChannel
from irerero_contract.validation import ReportCounts, validate_report
from pipelines.demo.config import REFERENCE_YEAR, SOURCE, WEEKS, rng, stable_id
from pipelines.demo.story import STORY_BY_ROLE

NO_WATER_WEEKS = {9: 0.62, 10: 0.5, 11: 0.42}  # week index -> attendance factor
JUMP_WEEK = 8
STOP_AFTER = 8
CHANNELS = {
    CentreType.HOME_BASED: (ReportChannel.SMS, ReportChannel.SMS, ReportChannel.WEB),
    CentreType.COMMUNITY_BASED: (ReportChannel.WEB, ReportChannel.OFFLINE, ReportChannel.SMS),
    CentreType.SCHOOL_BASED: (ReportChannel.WEB, ReportChannel.WEB, ReportChannel.OFFLINE),
    CentreType.CENTRE_BASED: (ReportChannel.WEB, ReportChannel.OFFLINE),
}


def _split(total: int, share: float) -> tuple[int, int]:
    first = round(total * share)
    return first, total - first


def _counts(
    r: random.Random,
    centre: dict[str, Any],
    enrolled: int,
    attendance: int,
    disability: int,
) -> ReportCounts:
    young_share = r.uniform(0.25, 0.4) if centre["serves_0_2"] else 0.0
    young, old = _split(enrolled, young_share)
    young_f, young_m = _split(young, r.uniform(0.45, 0.55))
    old_f, old_m = _split(old, r.uniform(0.45, 0.55))
    days_open = 6 if centre["type"] == CentreType.CENTRE_BASED.value else 5
    return ReportCounts(
        enrolled_0_2_female=young_f,
        enrolled_0_2_male=young_m,
        enrolled_3_6_female=old_f,
        enrolled_3_6_male=old_m,
        avg_daily_attendance=min(attendance, enrolled),
        waiting_list=max(0, round(r.gauss(2, 1.5))),
        caregivers_present=max(1, math.ceil(enrolled / 18)),
        days_open=days_open,
        days_meal_served=days_open if centre["offers_meals"] else 0,
        referrals_growth_monitoring=r.randint(0, 3) if centre["offers_growth_monitoring"] else 0,
        children_with_disability=min(enrolled, disability),
    )


def _series(centre: dict[str, Any]) -> list[tuple[int, ReportCounts, bool, MainProblem]]:
    """(week index, counts, wash available, main problem) for each week the centre reports."""
    r = rng(f"reports:{centre['code']}")
    disability = r.randint(0, 2)
    capacity = centre["capacity"]
    enrolled = round(capacity * r.uniform(0.62, 0.9))
    rows = []
    for week in range(len(WEEKS)):
        enrolled = max(5, min(capacity, enrolled + r.randint(-1, 1)))
        attendance = round(enrolled * r.uniform(0.8, 0.9))
        counts = _counts(r, centre, enrolled, attendance, disability)
        rows.append((week, counts, True, MainProblem.NONE))
    return rows


def _apply_story(
    code: str, rows: list[tuple[int, ReportCounts, bool, MainProblem]]
) -> list[tuple[int, ReportCounts, bool, MainProblem]]:
    story = {centre.code: role for role, centre in STORY_BY_ROLE.items()}
    role = story.get(code)
    out = []
    for week, counts, wash, problem in rows:
        if role == "caregiver_home" and week == len(WEEKS) - 1:
            continue  # this week's report is submitted live in the demo
        if role == "stopped_reporting" and week > STOP_AFTER:
            continue
        if role == "no_water" and week in NO_WATER_WEEKS:
            factor = NO_WATER_WEEKS[week]
            counts = _replace(
                counts, avg_daily_attendance=round(counts.avg_daily_attendance * factor)
            )
            wash, problem = False, MainProblem.NO_WATER
        if role == "overcrowded":
            enrolled = 78 + round(week * 1.3)
            young, old = _split(enrolled, 0.3)
            counts = _replace(
                counts,
                enrolled_0_2_female=young // 2,
                enrolled_0_2_male=young - young // 2,
                enrolled_3_6_female=old // 2,
                enrolled_3_6_male=old - old // 2,
                avg_daily_attendance=round(enrolled * 0.88),
                waiting_list=20 + week * 3,
                caregivers_present=3,
            )
        if role == "implausible_jump" and week == JUMP_WEEK:
            counts = _replace(
                counts,
                enrolled_3_6_female=counts.enrolled_3_6_female * 3,
                enrolled_3_6_male=counts.enrolled_3_6_male * 3,
                avg_daily_attendance=counts.avg_daily_attendance * 2,
                caregivers_present=counts.caregivers_present * 2,
            )
        out.append((week, counts, wash, problem))
    return out


def _replace(counts: ReportCounts, **changes: int) -> ReportCounts:
    return ReportCounts(**(asdict(counts) | changes))


INSERT_REPORT = text(
    """
    INSERT INTO weekly_report (id, centre_code, week_start, enrolled_0_2_female, enrolled_0_2_male,
        enrolled_3_6_female, enrolled_3_6_male, avg_daily_attendance, waiting_list,
        caregivers_present, days_open, days_meal_served, wash_available,
        referrals_growth_monitoring, children_with_disability, main_problem, channel,
        quality_flags, submitted_by, submitted_at, source, reference_year, origin,
        pipeline_run_id)
    VALUES (:id, :centre_code, :week_start, :enrolled_0_2_female, :enrolled_0_2_male,
        :enrolled_3_6_female, :enrolled_3_6_male, :avg_daily_attendance, :waiting_list,
        :caregivers_present, :days_open, :days_meal_served, :wash_available,
        :referrals_growth_monitoring, :children_with_disability, :main_problem, :channel,
        :quality_flags, :submitted_by, :submitted_at, :source, :year, 'simulated', :run_id)
    """
)


def build_reports(
    centres: list[dict[str, Any]], submitters: dict[str, object]
) -> list[dict[str, Any]]:
    reports = []
    for centre in centres:
        r = rng(f"report-meta:{centre['code']}")
        history: list[ReportCounts] = []
        channels = CHANNELS[CentreType(centre["type"])]
        for week, counts, wash, problem in _apply_story(centre["code"], _series(centre)):
            result = validate_report(counts, centre["capacity"], history, confirmed=True)
            if result.errors:
                raise ValueError(f"generator produced an invalid report: {centre['code']} {result}")
            week_start = WEEKS[week]
            submitted = datetime.combine(week_start + timedelta(days=4), time(15), tzinfo=UTC)
            reports.append(
                asdict(counts)
                | {
                    "id": stable_id("report", centre["code"], week_start),
                    "centre_code": centre["code"],
                    "week_start": week_start,
                    "wash_available": wash,
                    "main_problem": problem.value,
                    "channel": r.choice(channels).value,
                    "quality_flags": [flag.value for flag in result.flags],
                    "submitted_by": submitters.get(centre["code"]),
                    "submitted_at": submitted + timedelta(minutes=r.randint(0, 600)),
                }
            )
            history.append(counts)
    return reports


def load_reports(
    conn: Connection,
    run_id: object,
    centres: list[dict[str, Any]],
    submitters: dict[str, object],
) -> int:
    rows = build_reports(centres, submitters)
    meta = {"source": SOURCE, "year": REFERENCE_YEAR, "run_id": run_id}
    conn.execute(INSERT_REPORT, [row | meta for row in rows])
    return len(rows)
