"""IrereroAI in the app: the Overview hero (illustration, rotating notices, greeting, question
box, NST2 target), the conversation, and the "Ask IrereroAI" entry on every other screen.

One conversation per signed-in (or demo) user and session. A question is stored as pending and
the script reruns, so the question box is disabled while the answer streams; an interrupted
run records that it stopped instead of losing the question.
"""

import base64
from datetime import datetime
from functools import cache
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from irerero.assistant import chat, facts
from irerero.config import TARGET_2029, TARGET_YEAR
from irerero.roles import ANALYST, OFFICER, ROLE_LABELS, User
from irerero.ui import data, theme

STATE = "_assistant"
ART = theme.ASSETS / "assistant-bg.webp"
PAGES = {
    "national": "Overview",
    "priorities": "District priorities",
    "sector": "Sector diagnosis",
    "plan": "Action plans & progress",
    "brief": "District brief",
    "methods": "Data & methods",
    "officer": "Caregiver learning (sector officer)",
    "caregiver": "Caregiver learning (caregiver)",
    "admin": "Admin",
}
PLACEHOLDER = "Ask about your overview, district gaps or targets…"
# the hero's line and question box on each role's home screen
HERO = {
    "national": ("Understand your data. Explore district gaps. Plan your next steps.", PLACEHOLDER),
    "officer": ("Understand your sector. Follow up training. Plan your next visits.",
                "Ask about your sector, courses or check-ins…"),
    "caregiver": ("Understand pre-primary. Work through your courses. Prepare your check-in.",
                  "Ask about your courses or the monthly check-in…"),
    "admin": ("See which data are real. Check what is still simulated.",
              "Ask which datasets are real files and which are stand-ins…"),
}  # fmt: skip
PRIVACY = (
    "Answers are written by an AI model (Claude) from this dashboard's figures. Check them "
    "before you use them, and don't type personal information."
)


# --- configuration and state --------------------------------------------------------------
def config() -> chat.Config:
    try:
        secrets = dict(st.secrets)
    except Exception:  # no secrets file in this deployment
        secrets = {}
    return chat.Config.from_env(secrets)


def _state(user: User) -> dict[str, Any]:
    state = st.session_state.get(STATE)
    if state is None or state["user_id"] != (user.user_id, user.district_id):
        # a different (demo) user never sees the previous user's conversation
        state = {"user_id": (user.user_id, user.district_id), "display": [], "api": [],
                 "pending": None, "flash": None, "hidden": False}  # fmt: skip
        st.session_state[STATE] = state
    return state


def _questions(state: dict[str, Any]) -> int:
    return sum(1 for m in state["display"] if m["role"] == "user")


def _submit(key: str, page: str, user: User) -> None:
    state = _state(user)
    text = (st.session_state.get(key) or "").strip()
    if state["pending"]:
        return  # a question is already being answered
    if not text:
        state["flash"] = "Type a question first."
        return
    state["pending"] = {"text": text[: chat.MAX_QUESTION_CHARS], "page": page}
    state["hidden"] = False


def new_conversation(user: User) -> None:
    st.session_state.pop(STATE, None)
    _state(user)


# --- what the question is asked about -----------------------------------------------------
def _tables(target: float) -> facts.Tables:
    return facts.Tables(
        sectors=data.sectors(),
        forecast=data.table("forecast"),
        diagnosis=data.diagnosis_now(target),
        sources=data.sources().reset_index(),
        model_run=data.table("model_run"),
    )


def _plan_summary(district_id: str) -> dict[str, Any] | None:
    from irerero.track import plans

    plan_list = plans.plans(data.eng(), district_id)
    if not len(plan_list):
        return {"plan": "none yet"}
    row = plan_list.iloc[0]
    items = plans.items(data.eng(), int(row.plan_id))
    return {
        "name": row["name"],
        "status": "user input",
        "items": len(items),
        "decisions": items.decision.value_counts().to_dict(),
        "delivery_of_approved": items[items.decision.isin(["approved", "edited"])]
        .status.value_counts()
        .to_dict(),
        "approved_rooms": int(items[items.decision.isin(["approved", "edited"])].rooms.sum()),
    }


def _district_for(page: str, user: User) -> str | None:
    if user.role == ANALYST:
        key = {"priorities": "prio-district", "sector": "sector-district", "plan": "plan-d",
               "brief": "brief-d"}.get(page)  # fmt: skip
        ids = list(data.districts())
        return st.session_state.get(key, ids[0]) if key else None
    return user.district_id


def context(page: str, user: User, t: facts.Tables) -> chat.Context:
    target = data.target()
    selections: dict[str, Any] = {"reference_year": "2026 estimate (census 2022 base)"}
    on_screen: dict[str, Any] = {}
    district_id = _district_for(page, user)
    try:
        if page == "national":
            province = st.session_state.get("ov-province", "All provinces")
            selections["province"] = province
            on_screen = facts.overview(t, target, province)
        elif page in ("priorities", "brief", "plan") and district_id:
            preset = (
                st.session_state.get("preset", "Balanced") if page == "priorities" else "Balanced"
            )
            selections |= {"district": t.districts.get(district_id), "priority_preset": preset}
            t.plans = {district_id: _plan_summary(district_id)}
            on_screen = facts.district(t, district_id, target, preset)
        elif page == "sector" and district_id:
            geo_id = user.sector_id if user.role == OFFICER else st.session_state.get("sector_id")
            selections["district"] = t.districts.get(district_id)
            if geo_id:
                on_screen = facts.sector(t, geo_id, target)
                selections["sector"] = on_screen["sector"]
        elif page in ("methods", "admin"):
            on_screen = facts.data_status(t)
        elif page == "officer":
            on_screen = {"note": "This screen shows LEARN training and check-ins for the "
                         "officer's sector. Those are simulated pilot records the assistant "
                         "cannot read; it can explain the sector's diagnosis."}  # fmt: skip
        elif page == "caregiver":
            on_screen = {"note": "This screen is the caregiver's own check-in and courses; the "
                         "assistant does not read individual progress or quiz scores."}  # fmt: skip
    except (ValueError, KeyError) as exc:
        on_screen = {"unavailable": f"The figures for this screen could not be read ({exc})."}
    return chat.Context(PAGES.get(page, page), user, target, selections, on_screen)


# --- pieces -------------------------------------------------------------------------------
@cache
def _art_uri() -> str:
    return "data:image/webp;base64," + base64.b64encode(ART.read_bytes()).decode()


def _first_name() -> str | None:
    """The signed-in person's first name, when the deployment signs people in."""
    try:
        if st.user.is_logged_in:
            name = st.user.get("given_name") or st.user.get("name") or ""
            return str(name).split()[0] if name else None
    except Exception:  # sign-in not configured
        return None
    return None


def greeting(user: User) -> str:
    try:
        zone = ZoneInfo(st.context.timezone or "Africa/Kigali")
    except Exception:
        zone = ZoneInfo("Africa/Kigali")
    hour = datetime.now(zone).hour
    part = "morning" if hour < 12 else ("afternoon" if hour < 18 else "evening")
    name = _first_name()
    return f"Good {part}, {name}." if name else f"Good {part}."


def notices_html(simulated: bool) -> str:
    """Scope first, then the simulated-data warning: one at a time, rotating every 8 s,
    paused while pointed at or focused, stopped for good once a person picks one (and never
    moving when they ask for reduced motion). Both notices stay one click away, labelled in
    words, not colour."""
    scope = (
        f'<div class="ir-slide s1" role="group" aria-roledescription="slide" '
        f'aria-label="Scope"><span class="ir-slide-ico">{theme.icon("info", 18)}</span>'
        f"<div><b>Scope:</b> {escape(theme.DEFINITION)} Census, MINEDUC and NCDA enrolment "
        "figures are never added together.</div></div>"
    )
    if not simulated:
        return f'<div class="ir-notices single">{scope}</div>'
    warning = (
        '<div class="ir-slide s2 warn" role="group" aria-roledescription="slide" '
        f'aria-label="Simulated data warning"><span class="ir-slide-ico">{theme.icon("alert", 18)}'
        '</span><div><span class="ir-badge ir-sim">SIMULATED</span> Some values on this screen '
        "are simulated stand-ins for data files not yet loaded. They show the method, not the "
        "real situation, and are left out of exports by default.</div></div>"
    )
    controls = (
        '<div class="ir-notice-tabs" role="radiogroup" aria-label="Choose a notice">'
        '<label for="irn-1" class="t1"><span class="dot"></span>Scope</label>'
        '<label for="irn-2" class="t2"><span class="dot"></span>Simulated data</label></div>'
    )
    return (
        '<div class="ir-notices" role="region" aria-roledescription="carousel" '
        'aria-label="Notices: scope and simulated data">'
        '<input type="radio" name="irn" id="irn-1" class="ir-sr" aria-label="Show the scope">'
        '<input type="radio" name="irn" id="irn-2" class="ir-sr" '
        'aria-label="Show the simulated data warning">'
        f'<div class="ir-slides">{scope}{warning}</div>{controls}</div>'
    )


def _safe(text: str) -> str:
    """Model text for st.markdown: a dollar sign is not maths."""
    return text.replace("$", r"\$")


def _indicator(label: str) -> str:
    return (
        f'<div class="ir-typing" role="status"><span></span><span></span><span></span>'
        f"{escape(label)}…</div>"
    )


# --- the conversation ---------------------------------------------------------------------
def _history(state: dict[str, Any], user: User, scope: str) -> None:
    last = len(state["display"]) - 1
    for i, m in enumerate(state["display"]):
        with st.chat_message(m["role"], avatar=_avatar(m["role"])):
            _speaker(m["role"])
            if m.get("text"):
                st.markdown(_safe(m["text"]))
            if m.get("notice"):
                st.caption(m["notice"])
            if m.get("error"):
                st.markdown(
                    f'<div class="ir-notice ir-banner" role="alert">{theme.icon("alert", 16)}'
                    f"<div>{escape(m['error'])}</div></div>",
                    unsafe_allow_html=True,
                )
                if (
                    m.get("retry")
                    and i == last
                    and st.button("Try again", key=f"retry-{scope}-{i}", icon=":material/refresh:")
                ):
                    question = state["display"][i - 1]["text"]
                    del state["display"][i - 1 :]
                    state["pending"] = {"text": question, "page": m.get("page", "")}
                    st.rerun(scope="fragment" if scope == "dialog" else "app")


def _speaker(role: str) -> None:
    """Who is speaking, for screen readers (the avatars are images)."""
    who = "IrereroAI answered" if role == "assistant" else "You said"
    st.markdown(f'<span class="ir-sr">{who}:</span>', unsafe_allow_html=True)


def _avatar(role: str) -> str:
    return str(theme.ICON) if role == "assistant" else ":material/person:"


def _answer(state: dict[str, Any], page: str, user: User, scope: str) -> None:
    """Stream the answer to the pending question into the conversation."""
    cfg = config()
    pending = state["pending"]
    with st.chat_message("user", avatar=_avatar("user")):
        _speaker("user")
        st.markdown(_safe(pending["text"]))
    turn, error, done = None, None, False
    text = ""
    with st.chat_message("assistant", avatar=_avatar("assistant")):
        _speaker("assistant")
        status = st.empty()
        body = st.empty()
        status.markdown(_indicator("Reading the dashboard"), unsafe_allow_html=True)
        try:
            target = data.target()
            t = _tables(target)
            ctx = context(page, user, t)
            client = chat.make_client(cfg)
            for kind, value in chat.stream_turn(client, cfg, state["api"], pending["text"], ctx, t):
                if kind == "text":
                    if not text:
                        status.empty()  # the words themselves show progress now
                    text += value
                    body.markdown(_safe(text) + " ▍")
                elif kind == "reset":
                    text = value
                    body.markdown(_safe(text))
                elif kind == "status":
                    status.markdown(_indicator(value), unsafe_allow_html=True)
                elif kind == "done":
                    turn = value
                    status.empty()
            done = True
        except chat.AssistantError as exc:
            error, done = exc, True
        finally:
            state["pending"] = None
            q = {"role": "user", "text": pending["text"], "page": page}
            if not done:  # the run was interrupted (the person left the screen)
                state["display"] += [
                    q,
                    {
                        "role": "assistant",
                        "notice": "Stopped before the answer was complete. Ask again.",
                    },
                ]
    if error is not None:
        state["display"] += [q, {"role": "assistant", "error": error.message,
                                 "retry": error.retryable, "page": page}]  # fmt: skip
    elif turn is not None:
        state["api"] += turn.messages
        reply = {"role": "assistant", "text": turn.text, "notice": turn.notice}
        state["display"] += [q, reply]
    st.rerun(scope="fragment" if scope == "dialog" else "app")


def conversation(page: str, user: User, scope: str) -> None:
    """History, the answer in progress, and (in the dialog) the question box."""
    state = _state(user)
    _history(state, user, scope)
    if state["pending"]:
        _answer(state, page, user, scope)


def question_box(page: str, user: User, scope: str) -> None:
    state = _state(user)
    cfg = config()
    full = _questions(state) >= chat.MAX_QUESTIONS
    busy = bool(state["pending"])
    placeholder = HERO.get(page, HERO["national"])[1]
    if not cfg.ready:
        placeholder = "IrereroAI is not set up on this deployment yet"
    elif full:
        placeholder = "This conversation is full: start a new one"
    elif busy:
        placeholder = "IrereroAI is answering…"
    key = f"ask-{scope}"
    st.chat_input(
        placeholder,
        key=key,
        disabled=busy or full or not cfg.ready,
        max_chars=chat.MAX_QUESTION_CHARS,
        on_submit=_submit,
        args=(key, page, user),
    )
    if state.get("flash"):
        st.caption(state.pop("flash"))
        state["flash"] = None
    if not cfg.ready:
        theme.note(
            "The assistant needs an Anthropic API key. An administrator adds "
            "ANTHROPIC_API_KEY to the app's secrets (or environment) and restarts the app; "
            "see README, IrereroAI assistant."
        )


def _conversation_card(page: str, user: User) -> None:
    """Below the hero on a role's home screen, once there is something to show."""
    state = _state(user)
    if not state["display"] and not state["pending"]:
        return
    n = _questions(state) + (1 if state["pending"] else 0)
    with theme.panel(key="conversation"):
        head, hide, new = st.columns([6, 1.2, 1.6], vertical_alignment="center")
        head.markdown(
            f'<div class="ir-panel-head"><div><h3>{theme.icon("book", 20)}Conversation</h3>'
            f"<p>{n} question{'s' if n != 1 else ''} · answers from this dashboard's figures"
            "</p></div></div>",
            unsafe_allow_html=True,
        )
        if hide.button("Show" if state["hidden"] else "Hide", key="conv-hide",
                       width="stretch", disabled=bool(state["pending"])):  # fmt: skip
            state["hidden"] = not state["hidden"]
            st.rerun()
        if new.button("New conversation", key="conv-new", icon=":material/add_comment:",
                      width="stretch", disabled=bool(state["pending"])):  # fmt: skip
            new_conversation(user)
            st.rerun()
        if state["hidden"] and not state["pending"]:
            return
        with st.container(height=460, border=False, key="ir-chat-scroll"):
            conversation(page, user, "app")
        theme.note(PRIVACY)


def hero(user: User, simulated: bool, page: str = "national", sr_title: str | None = None) -> None:
    """The assistant's top area on each role's home screen: the robot scene as the backdrop
    of its left side, the notices, greeting, question box and NST2 target."""
    if sr_title:
        st.markdown(f'<h1 class="ir-title ir-sr">{escape(sr_title)}</h1>', unsafe_allow_html=True)
    st.markdown(  # the scene is decorative, so it is a background, not an image
        f"<style>.ir-hero-art {{ background-image: url({_art_uri()}); }}</style>",
        unsafe_allow_html=True,
    )
    area = data.districts().get(user.district_id, "") if user.district_id else "All districts"
    line = HERO.get(page, HERO["national"])[0]
    with st.container(key="ir-hero"):
        art, main = st.columns([1.3, 4], gap="small")
        art.markdown(
            '<div class="ir-hero-art ir-fill" aria-hidden="true"></div>', unsafe_allow_html=True
        )
        with main, st.container(key="hero-body"):
            notices, target = st.columns([2.6, 1.3], gap="small")
            notices.markdown(notices_html(simulated), unsafe_allow_html=True)
            target.markdown(
                theme.target_callout(
                    "NST2 target", f"{TARGET_2029.value:.0%} by {TARGET_YEAR}",
                    "Pre-primary enrolment",
                ).replace('class="ir-callout ir-target"', 'class="ir-callout ir-target ir-fill"'),
                unsafe_allow_html=True,
            )  # fmt: skip
            st.markdown(
                f'<div class="ir-greet"><div class="hello">{escape(greeting(user))}</div>'
                f'<div class="ask">Ask IrereroAI</div><div class="sub">{escape(line)}'
                f'<span class="who">{escape(ROLE_LABELS[user.role])} · {escape(area)}</span>'
                "</div></div>",
                unsafe_allow_html=True,
            )
            question_box(page, user, "app")
    _conversation_card(page, user)


@st.dialog("Ask IrereroAI", width="large")
def _dialog(page: str, user: User) -> None:
    state = _state(user)
    st.markdown(
        f'<div class="ir-note">Answers use the figures on <b>{escape(PAGES.get(page, page))}'
        "</b> and the app's data. Simulated values are labelled.</div>",
        unsafe_allow_html=True,
    )
    history = st.container(height=420, border=False, key="ir-chat-scroll-d")
    with st.container():  # drawn before the answer streams, so it shows as busy meanwhile
        question_box(page, user, "dialog")
    with history:
        if not state["display"] and not state["pending"]:
            st.markdown(theme.empty_state(_suggestion(page), "info"), unsafe_allow_html=True)
        conversation(page, user, "dialog")
    left, right = st.columns([3, 1])
    left.caption(PRIVACY)
    if right.button("New conversation", key="dlg-new", width="stretch",
                    disabled=bool(state["pending"]) or not state["display"]):  # fmt: skip
        new_conversation(user)
        st.rerun(scope="fragment")


def _suggestion(page: str) -> str:
    return {
        "priorities": "Ask why a sector ranks where it does, or how sure the order is.",
        "sector": "Ask what holds this sector back and what the suggested action means.",
        "plan": "Ask whether the district is on track, or how many places a year it needs.",
        "brief": "Ask for a plain-language summary of this brief.",
        "methods": "Ask what a status means, or which data are still simulated.",
        "officer": "Ask about your sector's diagnosis or the training rules.",
        "caregiver": "Ask what the scope of pre-primary means, or how the courses work.",
        "admin": "Ask which datasets are real files and which are stand-ins.",
    }.get(page, "Ask about the figures on this screen.")


def entry(page: str) -> None:
    """The compact "Ask IrereroAI" button for screens other than the Overview."""
    from irerero.ui.roles import current

    user = current()
    state = _state(user)
    label = "Ask IrereroAI" + (f" ({_questions(state)})" if state["display"] else "")
    clicked = st.button(label, key=f"ask-open-{page}", icon=":material/forum:",
                        help="Ask about the figures on this screen")  # fmt: skip
    if clicked or state["pending"]:  # a pending question left by a page rerun is finished
        _dialog(page, user)
