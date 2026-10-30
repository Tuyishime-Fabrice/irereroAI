"""District plans: recommendations become plan items, and a district planner approves, edits or
rejects each one. Edits and rejections need a reason. Every change goes to the audit log.

Only the planner of the district can decide. Analysts read; admins manage users and data but
cannot change decisions.
"""

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from irerero import audit
from irerero.db.models import Plan, PlanItem
from irerero.plan import gap
from irerero.roles import PLANNER, User

DECISIONS = ("approve", "edit", "reject")
DECIDED = {"approve": "approved", "edit": "edited", "reject": "rejected"}
STATUSES = ("planned", "funded", "done")


class NotAllowed(PermissionError):
    pass


def _check_planner(user: User, district_id: str) -> None:
    if user.role != PLANNER or user.district_id != district_id:
        raise NotAllowed("only the district planner of this district can change its plan")


def _item_dict(item: PlanItem) -> dict[str, Any]:
    return {
        "places": item.places,
        "rooms": item.rooms,
        "caregivers_low": item.caregivers_low,
        "caregivers_high": item.caregivers_high,
        "decision": item.decision,
        "status": item.status,
    }


def create_plan(
    eng: Engine,
    user: User,
    district_id: str,
    name: str,
    target: float,
    preset: str,
    weights: Mapping[str, float],
    items: Iterable[Mapping[str, Any]],
) -> int:
    """items: geo_id, rank, places, rooms, caregivers_low, caregivers_high, bottleneck,
    intervention."""
    _check_planner(user, district_id)
    with Session(eng) as s:
        plan = Plan(
            district_id=district_id,
            name=name,
            target=target,
            preset=preset,
            weights=dict(weights),
            created_by=user.user_id,
            created_at=audit.now(),
        )
        s.add(plan)
        s.flush()
        rows = [
            PlanItem(
                plan_id=plan.plan_id,
                geo_id=i["geo_id"],
                rank=int(i["rank"]),
                places=int(i["places"]),
                rooms=int(i["rooms"]),
                caregivers_low=int(i["caregivers_low"]),
                caregivers_high=int(i["caregivers_high"]),
                bottleneck=i["bottleneck"],
                intervention=i["intervention"],
                decision="pending",
                status="planned",
            )
            for i in items
        ]
        s.add_all(rows)
        audit.write(
            s,
            user,
            "plan.create",
            "plan",
            plan.plan_id,
            after={
                "name": name,
                "target": target,
                "preset": preset,
                "sectors": [r.geo_id for r in rows],
            },
        )
        s.commit()
        return plan.plan_id


def add_items(
    eng: Engine, user: User, plan_id: int, items: Iterable[Mapping[str, Any]]
) -> list[int]:
    """Add sectors to an existing plan as pending items (same fields as create_plan). Sectors
    already in the plan are skipped. Returns the new item ids."""
    with Session(eng) as s:
        plan = s.get(Plan, plan_id)
        if plan is None:
            raise KeyError(f"no plan {plan_id}")
        _check_planner(user, plan.district_id)
        existing = set(s.scalars(select(PlanItem.geo_id).where(PlanItem.plan_id == plan_id)))
        rows = [
            PlanItem(
                plan_id=plan_id,
                geo_id=i["geo_id"],
                rank=int(i["rank"]),
                places=int(i["places"]),
                rooms=int(i["rooms"]),
                caregivers_low=int(i["caregivers_low"]),
                caregivers_high=int(i["caregivers_high"]),
                bottleneck=i["bottleneck"],
                intervention=i["intervention"],
                decision="pending",
                status="planned",
            )
            for i in items
            if i["geo_id"] not in existing
        ]
        s.add_all(rows)
        s.flush()
        for row in rows:
            audit.write(
                s,
                user,
                "plan_item.add",
                "plan_item",
                row.id,
                after={**_item_dict(row), "geo_id": row.geo_id},
            )
        s.commit()
        return [row.id for row in rows]


def _load(s: Session, item_id: int) -> tuple[PlanItem, Plan]:
    item = s.get(PlanItem, item_id)
    if item is None:
        raise KeyError(f"no plan item {item_id}")
    plan = s.get(Plan, item.plan_id)
    assert plan is not None
    return item, plan


def decide(
    eng: Engine,
    user: User,
    item_id: int,
    decision: str,
    reason: str | None = None,
    places: int | None = None,
) -> None:
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    reason = (reason or "").strip() or None
    if decision in ("edit", "reject") and not reason:
        raise ValueError(f"a reason is required to {decision}")
    with Session(eng) as s:
        item, plan = _load(s, item_id)
        _check_planner(user, plan.district_id)
        if decision != "edit" and places is not None and int(places) != item.places:
            raise ValueError(
                f"places changed from {item.places:,} to {int(places):,}: choose edit, with a "
                "reason, to change the number of places"
            )
        before = _item_dict(item)
        if decision == "edit":
            if places is None or places < 0:
                raise ValueError("an edit sets the number of places")
            item.places = int(places)
            item.rooms = gap.rooms(item.places)
            item.caregivers_low, item.caregivers_high = gap.caregivers(item.places)
        item.decision = DECIDED[decision]
        item.reason = reason
        item.decided_by = user.user_id
        item.decided_at = audit.now()
        if decision == "reject":
            item.status = "planned"
        audit.write(
            s,
            user,
            f"plan_item.{decision}",
            "plan_item",
            item.id,
            before=before,
            after=_item_dict(item),
            reason=reason,
        )
        s.commit()


def set_status(
    eng: Engine, user: User, item_id: int, status: str, reason: str | None = None
) -> None:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    with Session(eng) as s:
        item, plan = _load(s, item_id)
        _check_planner(user, plan.district_id)
        if item.decision not in ("approved", "edited"):
            raise ValueError("only approved or edited items move to funded or done")
        before = _item_dict(item)
        item.status = status
        audit.write(
            s,
            user,
            "plan_item.status",
            "plan_item",
            item.id,
            before=before,
            after=_item_dict(item),
            reason=(reason or "").strip() or None,
        )
        s.commit()


def plans(eng: Engine, district_id: str | None = None) -> pd.DataFrame:
    query = select(Plan).order_by(Plan.created_at.desc())
    if district_id:
        query = query.where(Plan.district_id == district_id)
    with Session(eng) as s:
        return pd.DataFrame(
            [
                {
                    "plan_id": p.plan_id,
                    "district_id": p.district_id,
                    "name": p.name,
                    "target": p.target,
                    "preset": p.preset,
                    "created_by": p.created_by,
                    "created_at": p.created_at,
                }
                for p in s.scalars(query)
            ],
            columns=[
                "plan_id",
                "district_id",
                "name",
                "target",
                "preset",
                "created_by",
                "created_at",
            ],
        )


def items(eng: Engine, plan_id: int) -> pd.DataFrame:
    with Session(eng) as s:
        rows = s.scalars(
            select(PlanItem).where(PlanItem.plan_id == plan_id).order_by(PlanItem.rank)
        )
        return pd.DataFrame(
            [
                {
                    "id": i.id,
                    "geo_id": i.geo_id,
                    "rank": i.rank,
                    "places": i.places,
                    "rooms": i.rooms,
                    "caregivers_low": i.caregivers_low,
                    "caregivers_high": i.caregivers_high,
                    "bottleneck": i.bottleneck,
                    "intervention": i.intervention,
                    "decision": i.decision,
                    "reason": i.reason,
                    "status": i.status,
                    "decided_by": i.decided_by,
                    "decided_at": i.decided_at,
                }
                for i in rows
            ]
        )
