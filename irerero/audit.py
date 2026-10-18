"""Append-only audit log. Every decision, status change and course confirmation writes one row
with who, when, what changed and why. Rows can never be updated or deleted through the app."""

from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import Engine, event, select
from sqlalchemy.orm import Session

from irerero.db.models import AuditLog
from irerero.roles import User


class AuditImmutable(RuntimeError):
    pass


@event.listens_for(AuditLog, "before_update")
def _no_update(*_: Any) -> None:
    raise AuditImmutable("audit log rows cannot be changed")


@event.listens_for(AuditLog, "before_delete")
def _no_delete(*_: Any) -> None:
    raise AuditImmutable("audit log rows cannot be deleted")


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def write(
    s: Session,
    user: User,
    action: str,
    entity: str,
    entity_id: object,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AuditLog:
    row = AuditLog(
        at=now(),
        user_id=user.user_id,
        role=user.role,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        before=before,
        after=after,
        reason=reason,
    )
    s.add(row)
    return row


def read(
    eng: Engine, entity: str | None = None, entity_ids: list[str] | None = None
) -> pd.DataFrame:
    query = select(AuditLog).order_by(AuditLog.at.desc(), AuditLog.id.desc())
    if entity:
        query = query.where(AuditLog.entity == entity)
    if entity_ids is not None:
        query = query.where(AuditLog.entity_id.in_(entity_ids))
    with Session(eng) as s:
        rows = s.scalars(query).all()
        return pd.DataFrame(
            [
                {
                    "at": r.at,
                    "user_id": r.user_id,
                    "role": r.role,
                    "action": r.action,
                    "entity": r.entity,
                    "entity_id": r.entity_id,
                    "before": r.before,
                    "after": r.after,
                    "reason": r.reason,
                }
                for r in rows
            ],
            columns=[
                "at",
                "user_id",
                "role",
                "action",
                "entity",
                "entity_id",
                "before",
                "after",
                "reason",
            ],
        )
