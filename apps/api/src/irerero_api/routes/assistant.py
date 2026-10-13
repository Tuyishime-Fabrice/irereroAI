"""The "Why this suggestion?" assistant. It answers only from platform records and names them."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from irerero_api.auth.deps import require_roles
from irerero_api.auth.principal import Principal
from irerero_api.auth.scope import require_area, require_centre
from irerero_api.calendar import current_week
from irerero_api.config import get_settings
from irerero_api.db import get_session
from irerero_api.services.queries import alert_rows
from irerero_contract.enums import Role
from irerero_contract.tables import Alert, Recommendation, Scenario
from irerero_engine.assistant import AssistantContext, make_assistant
from irerero_engine.explain import number
from irerero_engine.types import SourceRef

router = APIRouter(prefix="/assistant", tags=["assistant"])
SessionDep = Annotated[Session, Depends(get_session)]
Staff = Annotated[
    Principal,
    Depends(
        require_roles(Role.SECTOR_OFFICER, Role.DISTRICT_PLANNER, Role.NATIONAL_ANALYST, Role.ADMIN)
    ),
]


class AskIn(BaseModel):
    subject: Literal["recommendation", "alert"]
    subject_id: uuid.UUID
    question: str = Field(min_length=1, max_length=300)
    language: Literal["en", "rw"] = "en"


class AnswerOut(BaseModel):
    question: str
    text: str
    tables: list[str]
    provider: str


def _recommendation_context(
    session: Session, principal: Principal, subject_id: uuid.UUID
) -> AssistantContext:
    from irerero_api.services.plan import scenario_out

    rec = session.get(Recommendation, subject_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown suggestion")
    scenario = session.get(Scenario, rec.scenario_id)
    assert scenario is not None
    require_area(session, principal, scenario.district_code)
    out = scenario_out(session, get_settings(), scenario)
    item = next(r for r in out.recommendations + out.rejected if r.id == rec.id)
    reached = item.children_reached
    return AssistantContext(
        subject=item.site_name,
        explanation_en=item.explanation_en,
        explanation_rw=item.explanation_rw,
        range_en=(
            f"The estimate is about {number(reached.estimate)} children, between "
            f"{number(reached.low)} and {number(reached.high)}. The range comes from the range of "
            "the child population estimate for the sectors in the catchment. Hatched areas on the "
            "map have the widest ranges."
        ),
        range_rw=(
            f"Igereranya ni abana bagera kuri {number(reached.estimate)}, hagati ya "
            f"{number(reached.low)} na {number(reached.high)}. Iyi ntera ituruka ku ntera "
            "y'igereranya ry'umubare w'abana mu mirenge iri hafi. Ahantu hasizwe imirongo ku "
            "ikarita ni ho hari intera nini kurusha ahandi."
        ),
        sources=[
            SourceRef(s.table, s.source, s.reference_year, s.origin.value) for s in item.sources
        ],
    )


def _alert_context(
    session: Session, principal: Principal, subject_id: uuid.UUID
) -> AssistantContext:
    alert = session.get(Alert, subject_id)
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown alert")
    require_centre(session, principal, alert.centre_code)
    row = alert_rows(session, current_week(get_settings()), alert_id=subject_id)[0]
    rule = f"{row.rule} ({row.model_version_id})"
    return AssistantContext(
        subject=row.centre_name,
        explanation_en=f"{row.reason_en} The signal comes from rule {rule}, which compares the "
        "centre with its own past weekly reports.",
        explanation_rw=f"{row.reason_rw} Iki kimenyetso gituruka ku itegeko {rule}, rigereranya "
        "irerero na raporo zaryo za buri cyumweru zabanje.",
        range_en="Early warning uses the reported counts directly; it has no estimate range. "
        "It can be wrong if a report was entered incorrectly, so check with the centre.",
        range_rw="Uburyo bwo kuburira hakiri kare bukoresha imibare yatanzwe uko iri; nta ntera "
        "y'igereranya bufite. Bushobora kwibeshya niba raporo yaranditswe nabi, bityo "
        "mubaze irerero.",
        sources=[
            SourceRef("alert", "IrereroAI early warning", row.week_start.year, row.origin),
            SourceRef("weekly_report", "IrereroAI weekly report", row.week_start.year, row.origin),
        ],
    )


@router.post("/ask", response_model=AnswerOut)
def ask(body: AskIn, session: SessionDep, principal: Staff) -> AnswerOut:
    if body.subject == "recommendation":
        context = _recommendation_context(session, principal, body.subject_id)
    else:
        context = _alert_context(session, principal, body.subject_id)
    answer = make_assistant(get_settings().llm_api_key).answer(
        body.question, body.language, context
    )
    return AnswerOut(
        question=answer.question,
        text=answer.text,
        tables=list(answer.tables),
        provider=answer.provider,
    )
