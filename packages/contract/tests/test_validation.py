from dataclasses import replace

from irerero_contract.enums import QualityFlag
from irerero_contract.validation import ReportCounts, validate_report

TYPICAL = ReportCounts(
    enrolled_0_2_female=5,
    enrolled_0_2_male=5,
    enrolled_3_6_female=10,
    enrolled_3_6_male=10,
    avg_daily_attendance=25,
    waiting_list=3,
    caregivers_present=2,
    days_open=5,
    days_meal_served=5,
    referrals_growth_monitoring=1,
    children_with_disability=1,
)


def test_typical_report_is_accepted_without_flags() -> None:
    result = validate_report(TYPICAL, capacity=40, history=[TYPICAL] * 4, confirmed=False)
    assert result.accepted
    assert result.flags == []


def test_attendance_above_enrolment_is_an_error_even_when_confirmed() -> None:
    report = replace(TYPICAL, avg_daily_attendance=31)
    result = validate_report(report, capacity=40, history=[], confirmed=True)
    assert not result.accepted
    assert [e.code for e in result.errors] == ["attendance_above_enrolment"]


def test_out_of_range_needs_confirmation_then_is_flagged() -> None:
    report = replace(TYPICAL, enrolled_3_6_female=40, enrolled_3_6_male=40, avg_daily_attendance=60)
    unconfirmed = validate_report(report, capacity=40, history=[], confirmed=False)
    assert not unconfirmed.accepted
    assert "enrolment_far_above_capacity" in [w.code for w in unconfirmed.warnings]

    confirmed = validate_report(report, capacity=40, history=[], confirmed=True)
    assert confirmed.accepted
    assert QualityFlag.OUT_OF_RANGE_CONFIRMED in confirmed.flags


def test_jump_against_own_history_is_flagged_not_rejected() -> None:
    report = replace(
        TYPICAL,
        enrolled_3_6_female=30,
        enrolled_3_6_male=30,
        avg_daily_attendance=60,
        caregivers_present=3,
    )
    result = validate_report(report, capacity=80, history=[TYPICAL] * 4, confirmed=False)
    assert result.accepted
    assert QualityFlag.ENROLMENT_JUMP in result.flags
    assert QualityFlag.ATTENDANCE_JUMP in result.flags


def test_small_change_at_small_centre_is_not_a_jump() -> None:
    small = replace(TYPICAL, enrolled_3_6_female=2, enrolled_3_6_male=2, avg_daily_attendance=10)
    bigger = replace(small, enrolled_3_6_female=6, enrolled_3_6_male=6, avg_daily_attendance=18)
    result = validate_report(bigger, capacity=40, history=[small] * 4, confirmed=False)
    assert result.flags == []
