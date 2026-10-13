"""EarlyWarning: rules over each centre's own reporting history, with plain-language reasons.

Phase 1 baseline: rolling z-scores of the attendance rate against the centre's own past, plus
missing-report, overcrowding, water and closure rules. Every alert carries the numbers it used.
Phase 2: an Isolation Forest, then a four-week risk classifier, implement the same interface.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from statistics import mean, pstdev
from typing import Protocol

from irerero_engine.explain import alert_reason

MIN_HISTORY = 4
HISTORY_WINDOW = 8
STD_FLOOR = 0.03  # attendance rates rarely vary less than this week to week
DROP_Z = -2.5
DROP_POINTS = 0.15  # and at least 15 percentage points below the usual rate
MISSING_WARNING = 2
MISSING_CRITICAL = 3


@dataclass(frozen=True)
class WeekReport:
    week_start: date
    enrolled: int
    attendance: int
    waiting_list: int
    days_open: int
    wash_available: bool
    main_problem: str

    @property
    def attendance_rate(self) -> float:
        return self.attendance / self.enrolled if self.enrolled else 0.0


@dataclass(frozen=True)
class CentreHistory:
    centre_code: str
    centre_name: str
    capacity: int
    reports: Sequence[WeekReport]


@dataclass(frozen=True)
class Signal:
    centre_code: str
    week_start: date
    kind: str
    severity: str
    rule: str
    reason_en: str
    reason_rw: str
    evidence: dict[str, float | int | str] = field(default_factory=dict)


class EarlyWarning(Protocol):
    version: str

    def check(self, centre: CentreHistory, weeks: Sequence[date]) -> list[Signal]: ...


def _consecutive(flags: Sequence[bool]) -> int:
    """How many of the most recent flags are true in a row."""
    run = 0
    for flag in reversed(flags):
        if not flag:
            break
        run += 1
    return run


class RuleBasedEarlyWarning:
    """Checks one centre as of the last week in `weeks` (the reporting calendar so far)."""

    version = "early-warning-rules-1"

    def check(self, centre: CentreHistory, weeks: Sequence[date]) -> list[Signal]:
        if not weeks:
            return []
        as_of = weeks[-1]
        by_week = {r.week_start: r for r in centre.reports if r.week_start <= as_of}
        signals = [
            s
            for s in (
                self._missing(centre, weeks, by_week),
                self._attendance_drop(centre, as_of, by_week),
                self._overcrowding(centre, as_of, by_week),
                self._wash(centre, as_of, by_week),
                self._closure(centre, as_of, by_week),
            )
            if s is not None
        ]
        return signals

    def _signal(
        self,
        centre: CentreHistory,
        week: date,
        kind: str,
        severity: str,
        rule: str,
        evidence: dict[str, float | int | str],
    ) -> Signal:
        en, rw = alert_reason(kind, centre.centre_name, evidence)
        return Signal(centre.centre_code, week, kind, severity, rule, en, rw, evidence)

    def _missing(
        self, centre: CentreHistory, weeks: Sequence[date], by_week: dict[date, WeekReport]
    ) -> Signal | None:
        missing = _consecutive([w not in by_week for w in weeks])
        if missing < MISSING_WARNING:
            return None
        severity = "critical" if missing >= MISSING_CRITICAL else "warning"
        last = max(by_week, default=None)
        evidence: dict[str, float | int | str] = {"weeks_missing": missing}
        if last is not None:
            evidence["last_report"] = last.isoformat()
        return self._signal(
            centre, weeks[-1], "missing_report", severity, "missing_weeks", evidence
        )

    def _attendance_drop(
        self, centre: CentreHistory, as_of: date, by_week: dict[date, WeekReport]
    ) -> Signal | None:
        ordered = [by_week[w] for w in sorted(by_week)]
        flags: list[bool] = []
        latest_evidence: dict[str, float | int | str] = {}
        for i, report in enumerate(ordered):
            past = ordered[max(0, i - HISTORY_WINDOW) : i]
            # Compare against weeks that were themselves normal, so a long drop stays visible.
            normal = [
                p for p, f in zip(past, flags[max(0, i - HISTORY_WINDOW) : i], strict=True) if not f
            ]
            if len(normal) < MIN_HISTORY:
                flags.append(False)
                continue
            usual = mean(p.attendance_rate for p in normal)
            spread = max(pstdev([p.attendance_rate for p in normal]), STD_FLOOR)
            z = (report.attendance_rate - usual) / spread
            dropped = z <= DROP_Z and usual - report.attendance_rate >= DROP_POINTS
            flags.append(dropped)
            if dropped:
                latest_evidence = {
                    "attendance": report.attendance,
                    "enrolled": report.enrolled,
                    "rate": round(report.attendance_rate, 3),
                    "usual_rate": round(usual, 3),
                    "z_score": round(z, 2),
                    "main_problem": report.main_problem,
                }
        if not ordered or ordered[-1].week_start != as_of:
            return None
        run = _consecutive(flags)
        if run < 2:
            return None
        latest_evidence["weeks"] = run
        severity = "critical" if run >= 3 else "warning"
        return self._signal(
            centre, as_of, "attendance_drop", severity, "attendance_z", latest_evidence
        )

    def _overcrowding(
        self, centre: CentreHistory, as_of: date, by_week: dict[date, WeekReport]
    ) -> Signal | None:
        recent = [by_week[w] for w in sorted(by_week)[-3:]]
        if not recent or recent[-1].week_start != as_of:
            return None
        over = [r for r in recent if r.attendance > centre.capacity]
        if len(over) < 2:
            return None
        latest = recent[-1]
        severity = "critical" if latest.waiting_list >= centre.capacity / 2 else "warning"
        evidence: dict[str, float | int | str] = {
            "attendance": latest.attendance,
            "capacity": centre.capacity,
            "waiting_list": latest.waiting_list,
        }
        return self._signal(
            centre, as_of, "overcrowding", severity, "attendance_over_capacity", evidence
        )

    def _wash(
        self, centre: CentreHistory, as_of: date, by_week: dict[date, WeekReport]
    ) -> Signal | None:
        ordered = [by_week[w] for w in sorted(by_week)]
        if not ordered or ordered[-1].week_start != as_of or ordered[-1].wash_available:
            return None
        run = _consecutive([not r.wash_available for r in ordered])
        severity = "critical" if run >= 2 else "warning"
        return self._signal(centre, as_of, "wash", severity, "no_wash", {"weeks": run})

    def _closure(
        self, centre: CentreHistory, as_of: date, by_week: dict[date, WeekReport]
    ) -> Signal | None:
        latest = by_week.get(as_of)
        if latest is None:
            return None
        if latest.days_open == 0 or latest.main_problem == "building_damage":
            evidence: dict[str, float | int | str] = {
                "days_open": latest.days_open,
                "main_problem": latest.main_problem,
            }
            return self._signal(
                centre, as_of, "closure_risk", "critical", "closed_or_damaged", evidence
            )
        return None


def reliability(reports: Sequence[tuple[date, bool]], weeks: Sequence[date]) -> float:
    """Share of the given weeks with an on-time report that carries no quality flags.

    `reports` is (week_start, has_quality_flags) per received report.
    """
    if not weeks:
        return 0.0
    clean = {week for week, flagged in reports if not flagged}
    return round(sum(week in clean for week in weeks) / len(weeks), 3)
