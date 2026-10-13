"""Write one append-only audit row per human decision."""

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from irerero_api.auth.principal import Principal
from irerero_contract.tables import AuditLog


def _jsonable(values: dict[str, Any] | None) -> dict[str, Any] | None:
    if values is None:
        return None
    out: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Enum):
            out[key] = value.value
        elif isinstance(value, uuid.UUID | date | datetime):
            out[key] = str(value)
        else:
            out[key] = value
    return out


def record(
    session: Session,
    principal: Principal,
    action: str,
    entity_type: str,
    entity_id: str,
    *,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=principal.id,
            actor_role=principal.role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=_jsonable(before),
            after=_jsonable(after),
            reason=reason,
        )
    )
