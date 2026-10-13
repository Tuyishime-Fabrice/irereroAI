"""Accepting a weekly report: validate with the shared rules, store, then re-run early warning."""

from dataclasses import asdict, dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from irerero_api.calendar import current_week, weeks_until
from irerero_api.config import Settings
from irerero_api.schemas.common import Issue
from irerero_api.schemas.reports import ReportIn, ValidationOut
from irerero_api.services.alerts import refresh_alerts
from irerero_api.services.reliability import refresh_reliability
from irerero_contract.enums import Origin, QualityFlag
from irerero_contract.tables import Centre, WeeklyReport
from irerero_contract.validation import ReportCounts, ValidationResult, validate_report
from irerero_engine.early_warning import RuleBasedEarlyWarning

SOURCE = "IrereroAI weekly report"
COUNT_FIELDS = tuple(ReportCounts.__dataclass_fields__)


class DuplicateReportError(Exception):
    pass


class WeekOutOfRangeError(Exception):
    pass


@dataclass(frozen=True)
class Outcome:
    validation: ValidationOut
    report: WeeklyReport | None


def counts_of(body: ReportIn | WeeklyReport) -> ReportCounts:
    return ReportCounts(**{name: getattr(body, name) for name in COUNT_FIELDS})


def to_out(result: ValidationResult) -> ValidationOut:
    return ValidationOut(
        accepted=result.accepted,
        errors=[Issue(**asdict(e)) for e in result.errors],
        warnings=[Issue(**asdict(w)) for w in result.warnings],
        flags=result.flags,
    )


def check(session: Session, body: ReportIn) -> ValidationResult:
    centre = session.get(Centre, body.centre_code)
    if centre is None:
        raise LookupError(body.centre_code)
    history = session.scalars(
        select(WeeklyReport)
        .where(
            WeeklyReport.centre_code == body.centre_code, WeeklyReport.week_start < body.week_start
        )
        .order_by(WeeklyReport.week_start)
    ).all()
    return validate_report(
        counts_of(body), centre.capacity, [counts_of(h) for h in history], confirmed=body.confirmed
    )


def submit(session: Session, body: ReportIn, submitted_by: object, settings: Settings) -> Outcome:
    this_week = current_week(settings)
    if body.week_start.weekday() != 0 or not (
        this_week - timedelta(weeks=12) <= body.week_start <= this_week
    ):
        raise WeekOutOfRangeError(body.week_start)
    existing = session.scalar(
        select(WeeklyReport.id).where(
            WeeklyReport.centre_code == body.centre_code, WeeklyReport.week_start == body.week_start
        )
    )
    if existing is not None:
        raise DuplicateReportError(body.week_start)
    result = check(session, body)
    if not result.accepted:
        return Outcome(to_out(result), None)

    flags = list(result.flags)
    if body.week_start < this_week - timedelta(weeks=1):
        flags.append(QualityFlag.LATE_SUBMISSION)
    centre = session.get(Centre, body.centre_code)
    assert centre is not None
    # A report about a simulated centre is itself simulated, even when typed in live.
    origin = Origin.SIMULATED if centre.origin is Origin.SIMULATED else Origin.PARTNER
    report = WeeklyReport(
        centre_code=body.centre_code,
        week_start=body.week_start,
        wash_available=body.wash_available,
        main_problem=body.main_problem,
        channel=body.channel,
        quality_flags=flags,
        submitted_by=submitted_by,
        source=SOURCE,
        reference_year=body.week_start.year,
        origin=origin,
        **{name: getattr(body, name) for name in COUNT_FIELDS},
    )
    session.add(report)
    session.flush()
    weeks = weeks_until(settings, body.week_start)
    conn = session.connection()
    refresh_alerts(conn, [body.centre_code], weeks, RuleBasedEarlyWarning(), origin)
    refresh_reliability(conn, [body.centre_code], weeks_until(settings))
    outcome = to_out(result)
    outcome.flags = flags
    return Outcome(outcome, report)


def week_status(session: Session, centre_code: str, week: date) -> bool:
    return (
        session.scalar(
            select(WeeklyReport.id).where(
                WeeklyReport.centre_code == centre_code, WeeklyReport.week_start == week
            )
        )
        is not None
    )
