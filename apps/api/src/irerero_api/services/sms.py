"""The coded SMS report, for basic phones.

    IR <centre> <week> <girls 0-2> <boys 0-2> <girls 3-6> <boys 3-6> <attendance> <waiting>
       <caregivers> <days open> <meal days> <water Y/N> <referrals> <disability> <problem> [OK]

<week> is the ISO week number. <problem> is a digit: 0 none, 1 no food, 2 no water,
3 caregiver absent, 4 building damage, 5 weather, 6 other. Ending with OK confirms values that
triggered a warning.

    IR ECD-GIC-001 39 6 5 12 13 30 2 2 5 5 Y 1 1 0
"""

from dataclasses import dataclass
from datetime import date

from irerero_contract.enums import MainProblem

KEYWORD = "IR"
COUNT_ORDER = (
    "enrolled_0_2_female",
    "enrolled_0_2_male",
    "enrolled_3_6_female",
    "enrolled_3_6_male",
    "avg_daily_attendance",
    "waiting_list",
    "caregivers_present",
    "days_open",
    "days_meal_served",
)
TAIL_ORDER = ("referrals_growth_monitoring", "children_with_disability")
PROBLEMS = list(MainProblem)  # index = SMS digit
TOKENS = 2 + 1 + len(COUNT_ORDER) + 1 + len(TAIL_ORDER) + 1


@dataclass(frozen=True)
class ParsedSms:
    centre_code: str
    week_start: date
    counts: dict[str, int]
    wash_available: bool
    main_problem: MainProblem
    confirmed: bool


class SmsFormatError(ValueError):
    """`code` is a stable key the clients translate."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def _week_start(week: int, current: date) -> date:
    year = current.isocalendar().year
    candidate = date.fromisocalendar(year, week, 1)
    if candidate > current:
        candidate = date.fromisocalendar(year - 1, week, 1)
    return candidate


def parse(text: str, current: date) -> ParsedSms:
    tokens = text.strip().upper().split()
    confirmed = bool(tokens) and tokens[-1] == "OK"
    if confirmed:
        tokens = tokens[:-1]
    if not tokens or tokens[0] != KEYWORD:
        raise SmsFormatError("missing_keyword")
    if len(tokens) != TOKENS:
        raise SmsFormatError("wrong_count", f"{len(tokens) - 1} of {TOKENS - 1}")
    centre, week_token, *rest = tokens[1:]
    numbers = rest[: len(COUNT_ORDER)]
    wash, referrals, disability, problem = rest[len(COUNT_ORDER) :]
    try:
        week = int(week_token)
        counts = dict(zip(COUNT_ORDER, (int(n) for n in numbers), strict=True))
        counts |= dict(zip(TAIL_ORDER, (int(referrals), int(disability)), strict=True))
        problem_index = int(problem)
    except ValueError as error:
        raise SmsFormatError("not_a_number") from error
    if not 1 <= week <= 53:
        raise SmsFormatError("bad_week")
    if wash not in {"Y", "N"}:
        raise SmsFormatError("bad_water")
    if not 0 <= problem_index < len(PROBLEMS):
        raise SmsFormatError("bad_problem")
    return ParsedSms(
        centre_code=centre,
        week_start=_week_start(week, current),
        counts=counts,
        wash_available=wash == "Y",
        main_problem=PROBLEMS[problem_index],
        confirmed=confirmed,
    )


def example(centre_code: str, week: date) -> str:
    return f"IR {centre_code} {week.isocalendar().week} 6 5 12 13 30 2 2 5 5 Y 1 1 0"
