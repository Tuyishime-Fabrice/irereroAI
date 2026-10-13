from datetime import date, timedelta

from irerero_engine.early_warning import (
    CentreHistory,
    RuleBasedEarlyWarning,
    WeekReport,
    reliability,
)

WEEKS = [date(2026, 7, 6) + timedelta(weeks=i) for i in range(12)]
RATES = [0.84, 0.86, 0.82, 0.85, 0.88, 0.83, 0.86, 0.84, 0.85, 0.87, 0.83, 0.86]


def week(i: int, attendance: int, **changes: object) -> WeekReport:
    values: dict[str, object] = {
        "week_start": WEEKS[i],
        "enrolled": 40,
        "attendance": attendance,
        "waiting_list": 2,
        "days_open": 5,
        "wash_available": True,
        "main_problem": "none",
    }
    values.update(changes)
    return WeekReport(**values)  # type: ignore[arg-type]


def clean(capacity: int = 50) -> CentreHistory:
    reports = [week(i, round(40 * r)) for i, r in enumerate(RATES)]
    return CentreHistory("C", "Clean centre", capacity, reports)


def kinds(history: CentreHistory, upto: int = 12) -> set[str]:
    return {s.kind for s in RuleBasedEarlyWarning().check(history, WEEKS[:upto])}


def test_clean_centre_raises_nothing() -> None:
    for upto in range(1, 13):
        assert kinds(clean(), upto) == set()


def test_attendance_drop_needs_two_weeks_and_names_the_problem() -> None:
    history = clean()
    reports = list(history.reports)
    for i in (9, 10, 11):
        reports[i] = week(i, 14, wash_available=False, main_problem="no_water")
    dropped = CentreHistory("C", "Umucyo", 50, reports)
    assert "attendance_drop" not in kinds(dropped, 10)
    signals = RuleBasedEarlyWarning().check(dropped, WEEKS)
    drop = next(s for s in signals if s.kind == "attendance_drop")
    assert drop.severity == "critical"
    assert "no water" in drop.reason_en
    assert "nta mazi" in drop.reason_rw
    assert "wash" in kinds(dropped)


def test_missing_reports_count_consecutive_weeks() -> None:
    history = CentreHistory("C", "Amahoro", 30, clean().reports[:9])
    assert kinds(history, 10) == set()
    assert kinds(history, 11) == {"missing_report"}
    critical = RuleBasedEarlyWarning().check(history, WEEKS)
    assert critical[0].severity == "critical"


def test_only_current_week_missing_is_not_an_alert() -> None:
    history = CentreHistory("C", "Ineza", 50, clean().reports[:11])
    assert kinds(history) == set()


def test_overcrowding_and_closure() -> None:
    crowded = CentreHistory("C", "Urumuri", 30, clean().reports)
    assert "overcrowding" in kinds(crowded)
    closed = list(clean().reports)
    closed[11] = week(11, 0, days_open=0)
    assert "closure_risk" in kinds(CentreHistory("C", "X", 50, closed))


def test_reliability_counts_clean_on_time_weeks() -> None:
    reports = [(w, i == 3) for i, w in enumerate(WEEKS[:10])]
    assert reliability(reports, WEEKS) == round(9 / 12, 3)
