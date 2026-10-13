"""Weekly report validation, shared by the API, the SMS parser and the Phase 2 adapters.

Three outcomes, never a silent accept:
- errors block the report (impossible values, e.g. attendance above enrolment);
- warnings need the reporter to confirm (unusual but possible values);
- quality flags are stored with the report and shown to the sector officer.

Results carry codes and numbers only; the clients render them in English or Kinyarwanda.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from statistics import median

from irerero_contract.enums import QualityFlag

# A jump is flagged when the change against the centre's recent median exceeds both limits,
# so small centres are not flagged for a change of two or three children.
JUMP_SHARE = 0.3
JUMP_MIN_CHILDREN = 10
HISTORY_WEEKS = 4
MAX_ENROLMENT_TO_CAPACITY = 1.5
MAX_CHILDREN_PER_CAREGIVER = 25
MAX_WAITING_TO_CAPACITY = 3.0


@dataclass(frozen=True)
class ReportCounts:
    enrolled_0_2_female: int
    enrolled_0_2_male: int
    enrolled_3_6_female: int
    enrolled_3_6_male: int
    avg_daily_attendance: int
    waiting_list: int
    caregivers_present: int
    days_open: int
    days_meal_served: int
    referrals_growth_monitoring: int
    children_with_disability: int

    @property
    def enrolled(self) -> int:
        return (
            self.enrolled_0_2_female
            + self.enrolled_0_2_male
            + self.enrolled_3_6_female
            + self.enrolled_3_6_male
        )


@dataclass(frozen=True)
class Issue:
    code: str
    field: str
    params: dict[str, int | float] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    errors: list[Issue]
    warnings: list[Issue]
    """Unconfirmed warnings. Empty once the reporter confirms."""
    flags: list[QualityFlag]

    @property
    def accepted(self) -> bool:
        return not self.errors and not self.warnings


def _errors(r: ReportCounts) -> list[Issue]:
    errors = []
    for name, value in vars(r).items():
        if value < 0:
            errors.append(Issue("negative", name))
    for name in ("days_open", "days_meal_served"):
        if getattr(r, name) > 6:
            errors.append(Issue("days_above_six", name))
    if r.avg_daily_attendance > r.enrolled:
        errors.append(
            Issue(
                "attendance_above_enrolment",
                "avg_daily_attendance",
                {"attendance": r.avg_daily_attendance, "enrolled": r.enrolled},
            )
        )
    if r.days_meal_served > r.days_open:
        errors.append(Issue("meals_above_days_open", "days_meal_served"))
    if r.children_with_disability > r.enrolled:
        errors.append(Issue("disability_above_enrolment", "children_with_disability"))
    if r.days_open == 0 and r.avg_daily_attendance > 0:
        errors.append(Issue("attendance_while_closed", "avg_daily_attendance"))
    return errors


def _warnings(r: ReportCounts, capacity: int) -> list[Issue]:
    warnings = []
    if r.enrolled > capacity * MAX_ENROLMENT_TO_CAPACITY:
        warnings.append(
            Issue(
                "enrolment_far_above_capacity",
                "enrolled",
                {"enrolled": r.enrolled, "capacity": capacity},
            )
        )
    if r.days_open > 0 and r.caregivers_present == 0:
        warnings.append(Issue("no_caregiver_while_open", "caregivers_present"))
    elif (
        r.caregivers_present
        and r.avg_daily_attendance / r.caregivers_present > MAX_CHILDREN_PER_CAREGIVER
    ):
        warnings.append(
            Issue(
                "children_per_caregiver_high",
                "caregivers_present",
                {"ratio": round(r.avg_daily_attendance / r.caregivers_present, 1)},
            )
        )
    if r.waiting_list > capacity * MAX_WAITING_TO_CAPACITY:
        warnings.append(
            Issue("waiting_list_very_long", "waiting_list", {"waiting": r.waiting_list})
        )
    return warnings


def _jumped(current: int, history: Sequence[int]) -> bool:
    if not history:
        return False
    reference = median(history)
    change = abs(current - reference)
    return change > JUMP_MIN_CHILDREN and change > JUMP_SHARE * max(reference, 1)


def validate_report(
    report: ReportCounts,
    capacity: int,
    history: Sequence[ReportCounts],
    *,
    confirmed: bool,
) -> ValidationResult:
    """Validate one report against hard rules, expected ranges and the centre's own history.

    `history` is the centre's previous reports, most recent last. `confirmed` is true when the
    reporter has seen the warnings and confirmed the values.
    """
    errors = _errors(report)
    warnings = _warnings(report, capacity)
    recent = history[-HISTORY_WEEKS:]
    flags = []
    if _jumped(report.enrolled, [h.enrolled for h in recent]):
        flags.append(QualityFlag.ENROLMENT_JUMP)
    if _jumped(report.avg_daily_attendance, [h.avg_daily_attendance for h in recent]):
        flags.append(QualityFlag.ATTENDANCE_JUMP)
    if warnings and confirmed:
        flags.append(QualityFlag.OUT_OF_RANGE_CONFIRMED)
    return ValidationResult(errors=errors, warnings=[] if confirmed else warnings, flags=flags)
