"""IrereroAI assistant: Claude, answering from the dashboard's own figures.

The model sees a frozen system prompt (method, definitions, rules), a fixed tool set that reads
the dashboard tables through irerero.assistant.facts, and, with each question, a snapshot of
the screen the person is on. Conversations are append-only: earlier turns, including the
model's thinking and tool calls, go back unchanged, which keeps thinking blocks valid and the
prompt cache warm. Role permissions are enforced when a tool runs, so the tool list never
changes during a conversation.

No figure is computed here. Without an API key the assistant reports that it is not
configured; it never pretends to answer.
"""

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import anthropic

from irerero.assistant import facts
from irerero.config import (
    CAREGIVER_RATIO_HIGH,
    CAREGIVER_RATIO_LOW,
    CHILDREN_PER_ROOM,
    DEFINITION,
    MILESTONE_YEAR,
    SUPPRESS_BELOW,
    TARGET_2027,
    TARGET_2029,
    TARGET_YEAR,
    WALKING_DISTANCE_KM,
)
from irerero.roles import ADMIN, ANALYST, CAREGIVER, OFFICER, PLANNER, ROLE_LABELS, User

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"
MAX_TOKENS = 16000
MAX_TOOL_ROUNDS = 6
MAX_QUESTIONS = 20
MAX_QUESTION_CHARS = 2000
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class Config:
    api_key: str | None
    model: str = DEFAULT_MODEL
    effort: str = DEFAULT_EFFORT
    base_url: str | None = None
    fallbacks: bool = True
    """Server-side refusal fallback ("default" routing). Off if the account rejects it."""

    @property
    def ready(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def from_env(cls, secrets: dict[str, Any] | None = None) -> "Config":
        """Secrets (Streamlit's st.secrets) win over environment variables."""

        def get(key: str) -> Any:
            return (secrets or {}).get(key) or os.environ.get(key)

        return cls(
            api_key=get("ANTHROPIC_API_KEY"),
            model=get("IRERERO_ASSISTANT_MODEL") or DEFAULT_MODEL,
            effort=get("IRERERO_ASSISTANT_EFFORT") or DEFAULT_EFFORT,
            base_url=get("IRERERO_ASSISTANT_BASE_URL"),
            fallbacks=str(get("IRERERO_ASSISTANT_FALLBACKS") or "on").lower()
            not in ("0", "off", "false", "no"),
        )


class AssistantError(Exception):
    """A failure to show the person, in words they can act on."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


SYSTEM = f"""You are IrereroAI, the assistant inside a planning dashboard for early childhood \
development (ECD) in Rwanda. Your users are district planners, national analysts, sector \
officers and NCDA/MINEDUC staff. Help them read the dashboard: KPIs, charts, maps, district \
and sector gaps, the 2028/29 target, and what the figures mean for planning.

How to answer
- Use only figures from the <dashboard_context> block sent with each question or from your \
tools. Never estimate, invent or round up a figure, source, district or conclusion that \
these do not give. If the data needed is not available, say so plainly and say which \
dataset would answer it.
- Every figure carries a status. Say it whenever a figure matters to the answer: \
"observed", "published estimate", "model estimate" or "simulated". Simulated values are \
stand-ins for data files not yet loaded: they show the method, not the real situation. \
Never present a simulated value as a real-world fact; say "simulated" next to it.
- Only say a district or sector has the greatest need if the figures you were given show \
it, and say by which measure (places needed, share not attending, projected rate).
- Drivers from the peer model are associations, not causes. Do not claim causes.
- Be concise: lead with the answer in one or two sentences, then at most five short \
bullets. Plain language, no jargon without a gloss. Use the user's numbers format \
(1,234; 32.5%). Do not use tables wider than four columns.
- You cannot change plans, weights or data. Point people to the screen that does it: \
District priorities (ranking and weights), Sector diagnosis, Action plans & progress \
(decisions, what-if), District brief (exports), Data & methods (sources, model card).
- Tools refuse what the person's role may not see; explain that instead of guessing.
- Do not ask for or repeat personal data. The dashboard holds aggregates only; caregivers \
are never ranked and quiz scores are private.
- The question may arrive in English, French or Kinyarwanda; answer in the same language.

Definitions and method (from the dashboard)
- Scope: {DEFINITION} Census, MINEDUC and NCDA enrolment figures are never added together.
- Targets: NST2 aims for {TARGET_2029.value:.0%} pre-primary enrolment by {TARGET_YEAR} \
and {TARGET_2027.value:.1%} by {MILESTONE_YEAR} ({TARGET_2029.citation}). The target \
attendance slider changes the target used for places and status; the NST2 figure does not \
change.
- 2026 children aged 3 to 5: NISR district projection times the census 3-5 share, split \
across sectors by WorldPop under-5 or census shares, with a range.
- Attending (2026): the sector's census 2022 attendance rate moved by the district's change \
in MINEDUC pupils per child since 2021/22.
- Places = max(0, ceil(target x children) - attending). Rooms = ceil(places / \
{CHILDREN_PER_ROOM.value:g}). Caregivers between places/{CAREGIVER_RATIO_HIGH.value:g} and \
places/{CAREGIVER_RATIO_LOW.value:g} ({CHILDREN_PER_ROOM.citation}).
- Distance: share of children more than {WALKING_DISTANCE_KM.value:g} km from a school, \
along roads where OSM roads reach most children, otherwise straight-line (indicative).
- Priority index: weighted percentile ranks within one district of volume (places), equity \
(share not attending), peer gap (below the peer model) and poverty; presets Reach most \
children, Equity first, Balanced. Rank stability: share of 500 random weightings in which a \
sector stays in the top 3. Districts are compared by places needed, not by this index.
- Peer model: expected attendance from similar sectors (leave-one-district-out validation, \
80% conformal interval); a sector below its interval is behind its peers.
- Bottlenecks, by explicit rules: SUPPLY (large gap and many children far from school), \
DEMAND (school nearby, attendance below peers), CAPACITY (teacher ratios or qualifications \
in the worst quarter, district context), WELLBEING (stunting, water or sanitation in the \
worst quarter), NONE (at or above target).
- TRACK: gross enrolment rate = MINEDUC pre-primary pupils / children aged 3 to 5, linear \
trend over 2020/21-2024/25 with an 80% prediction range; on track, at risk or off track \
against the target. Five yearbook points make a short trend.
- Limitations: census attendance may miss home-based ECD; the 3-5 share is held at 2022; \
OSM does not mark pre-primary; district context is applied to every sector; LEARN data \
are a simulated Muhanga pilot. Exports show counts under {SUPPRESS_BELOW} as \
"fewer than {SUPPRESS_BELOW}".
"""


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "eager_input_streaming": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


_TARGET = {"type": "number", "description": "Target attendance as a share, e.g. 0.65. "
           "Omit to use the dashboard's current target."}  # fmt: skip
TOOLS = [
    _tool(
        "get_overview",
        "National or provincial overview: 2026 children aged 3-5, attendance, places, rooms, "
        "distance, the national 2028/29 trend, district status counts and the districts "
        "needing most places.",
        {"province": {"type": "string", "description": "Province name, or omit for Rwanda."},
         "target": _TARGET},
        [],
    ),
    _tool(
        "compare_districts",
        "All districts (or one province's) side by side, sorted by a measure: places_needed, "
        "attending_pct, projected_2028_29_pct or children_not_attending.",
        {"sort_by": {"type": "string", "enum": ["places_needed", "attending_pct",
                     "projected_2028_29_pct", "children_not_attending"]},
         "province": {"type": "string"}, "target": _TARGET},
        [],
    ),
    _tool(
        "get_district",
        "One district: needs, 2028/29 trend and status, places a year still needed, "
        "bottleneck mix, action plan summary, and its sector priority ranking.",
        {"district": {"type": "string", "description": "District name, e.g. Muhanga."},
         "preset": {"type": "string", "enum": ["Reach most children", "Equity first",
                    "Balanced"]},
         "target": _TARGET},
        ["district"],
    ),
    _tool(
        "get_sector",
        "One sector's diagnosis: attendance, places short, main bottleneck and suggested "
        "action, factor scores, observed vs expected attendance and top drivers.",
        {"district": {"type": "string"}, "sector": {"type": "string"}, "target": _TARGET},
        ["district", "sector"],
    ),
    _tool(
        "get_data_status",
        "Which datasets are real files and which are simulated stand-ins, and the peer "
        "model's validation.",
        {},
        [],
    ),
]  # fmt: skip
TOOL_NAMES = {t["name"] for t in TOOLS}

# What each role may read through the tools, mirroring the screens it can open.
ALLOWED = {
    PLANNER: {"get_overview", "compare_districts", "get_district", "get_sector",
              "get_data_status"},
    ANALYST: {"get_overview", "compare_districts", "get_district", "get_sector",
              "get_data_status"},
    OFFICER: {"get_district", "get_sector", "get_data_status"},
    CAREGIVER: {"get_data_status"},
    ADMIN: {"get_data_status"},
}  # fmt: skip


@dataclass
class Context:
    """The screen the question was asked from."""

    page: str
    user: User
    target: float
    selections: dict[str, Any] = field(default_factory=dict)
    on_screen: dict[str, Any] = field(default_factory=dict)

    def block(self, tables: facts.Tables) -> str:
        area = (
            tables.districts.get(self.user.district_id, self.user.district_id)
            if self.user.district_id
            else "all districts"
        )
        payload = {
            "page": self.page,
            "role": ROLE_LABELS[self.user.role],
            "area": area,
            "filters": {"target_attendance_pct": round(self.target * 100), **self.selections},
            "targets": facts.targets(),
            "data_status": facts.data_status(tables),
            "on_screen": self.on_screen,
        }
        return (
            "<dashboard_context>\n"
            + json.dumps(payload, ensure_ascii=False, default=str)
            + "\n</dashboard_context>"
        )


def _check_scope(user: User, district_id: str, sector_detail: bool) -> None:
    """Planners read sector detail for their own district only; sector officers read their
    own district only. Checked before any sector name is looked up."""
    if user.role == OFFICER and district_id != user.district_id:
        raise PermissionError("Sector officers see their own district and sector only.")
    if user.role == PLANNER and sector_detail and district_id != user.district_id:
        raise PermissionError("Planners see sector detail for their own district only.")


def run_tool(name: str, args: Any, ctx: Context, tables: facts.Tables) -> dict[str, Any]:
    """Run one tool call. Raises ValueError (bad input), PermissionError or facts.NotFound."""
    if name not in TOOL_NAMES:
        raise ValueError(f"unknown tool {name}")
    if not isinstance(args, dict):
        raise ValueError("tool input must be an object")
    if name not in ALLOWED.get(ctx.user.role, set()):
        raise PermissionError(
            f"The {ROLE_LABELS[ctx.user.role]} role cannot open this information in the app."
        )
    for key, value in args.items():
        if key == "target":
            if not isinstance(value, int | float) or not 0 < value <= 1:
                raise ValueError("target must be a share between 0 and 1")
        elif not isinstance(value, str):
            raise ValueError(f"{key} must be text")
    target = float(args.get("target") or ctx.target)
    if name == "get_overview":
        return facts.overview(tables, target, args.get("province"))
    if name == "compare_districts":
        return facts.compare_districts(
            tables, target, args.get("sort_by", "places_needed"), args.get("province")
        )
    if name == "get_data_status":
        return facts.data_status(tables)
    district_id = facts.find_district(tables, args.get("district", ""))
    if name == "get_district":
        _check_scope(ctx.user, district_id, sector_detail=False)
        detail = ctx.user.role == ANALYST or district_id == ctx.user.district_id
        return facts.district(
            tables, district_id, target, args.get("preset", "Balanced"), sectors=detail
        )
    _check_scope(ctx.user, district_id, sector_detail=True)
    sector_id = facts.find_sector(tables, args.get("sector", ""), district_id)
    if ctx.user.role == OFFICER and sector_id != ctx.user.sector_id:
        raise PermissionError("Sector officers see their own sector only.")
    return facts.sector(tables, sector_id, target)


# --- the conversation ---------------------------------------------------------------------
def _block(block: Any) -> dict[str, Any] | None:
    """A response content block as a request block, unchanged in every field that matters."""
    kind = block.type
    if kind == "text":
        return {"type": "text", "text": block.text}
    if kind == "thinking":
        return {"type": "thinking", "thinking": block.thinking, "signature": block.signature}
    if kind == "redacted_thinking":
        return {"type": "redacted_thinking", "data": block.data}
    if kind == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    if kind == "fallback":
        return None  # an audit marker; the API ignores it
    return block.model_dump(mode="json", exclude_none=True)


def assistant_content(content: list[Any]) -> list[dict[str, Any]]:
    """Echo rules after a mid-output fallback: drop thinking and tool_use blocks that came
    before the last fallback marker; keep text and everything after it."""
    last = max((i for i, b in enumerate(content) if b.type == "fallback"), default=-1)
    out = []
    for i, b in enumerate(content):
        if i < last and b.type in ("thinking", "redacted_thinking", "tool_use"):
            continue
        block = _block(b)
        if block is not None:
            out.append(block)
    return out


@dataclass
class Turn:
    text: str
    messages: list[dict[str, Any]]
    """Request messages this turn adds to the history (user, assistant, tool rounds)."""
    stop_reason: str
    notice: str | None = None
    tools_used: list[str] = field(default_factory=list)


def make_client(config: Config) -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=config.api_key,
        base_url=config.base_url,
        max_retries=2,
        timeout=anthropic.Timeout(120.0, connect=10.0),
    )


STATUS_TEXT = {
    "get_overview": "Reading the overview figures",
    "compare_districts": "Comparing districts",
    "get_district": "Reading the district's figures",
    "get_sector": "Reading the sector diagnosis",
    "get_data_status": "Checking which data are real",
}


def _error(exc: Exception, config: Config) -> AssistantError:
    """Typed SDK errors, most specific first, to a message a person can act on."""
    if isinstance(exc, anthropic.AuthenticationError):
        return AssistantError(
            "The AI service rejected the configured API key. An administrator needs to "
            "check ANTHROPIC_API_KEY.",
            retryable=False,
        )
    if isinstance(exc, anthropic.PermissionDeniedError):
        return AssistantError(
            "The configured API key is not allowed to use this model.", retryable=False
        )
    if isinstance(exc, anthropic.NotFoundError):
        return AssistantError(
            f"The model '{config.model}' is not available to this API key. Set "
            "IRERERO_ASSISTANT_MODEL to a model the key can use.",
            retryable=False,
        )
    if isinstance(exc, anthropic.RateLimitError):
        wait = exc.response.headers.get("retry-after") if exc.response is not None else None
        return AssistantError(
            "IrereroAI is receiving too many requests right now. "
            + (f"Try again in about {wait} seconds." if wait else "Try again in a minute.")
        )
    if isinstance(exc, anthropic.BadRequestError):
        return AssistantError(
            f"The AI service could not process this conversation ({exc.message}). Start a "
            "new conversation and try again.",
            retryable=False,
        )
    if isinstance(exc, anthropic.APIStatusError):
        return AssistantError(
            "The AI service is temporarily unavailable"
            f" (error {exc.status_code}). Try again shortly."
        )
    if isinstance(exc, anthropic.APITimeoutError):
        return AssistantError("The AI service took too long to answer. Try again.")
    if isinstance(exc, anthropic.APIConnectionError):
        return AssistantError(
            "Could not reach the AI service. Check the network connection and try again."
        )
    if isinstance(exc, anthropic.CredentialsError):
        return AssistantError("No API key is configured for IrereroAI.", retryable=False)
    return AssistantError(f"Something went wrong while answering ({type(exc).__name__}).")


def stream_turn(
    client: anthropic.Anthropic,
    config: Config,
    history: list[dict[str, Any]],
    question: str,
    ctx: Context,
    tables: facts.Tables,
) -> Iterator[tuple[str, Any]]:
    """Answer one question. Yields ("text", chunk) and ("status", label) as they happen, then
    ("done", Turn). Raises AssistantError; the history is unchanged when it does."""
    user = {
        "role": "user",
        "content": [
            {"type": "text", "text": ctx.block(tables)},
            {"type": "text", "text": question},
        ],
    }
    messages = [*history, user]
    added: list[dict[str, Any]] = [user]
    text: list[str] = []
    used: list[str] = []
    extra: dict[str, Any] = (
        {"betas": [FALLBACK_BETA], "fallbacks": "default"} if config.fallbacks else {}
    )
    json_retries = 0
    rounds = 0
    while True:
        round_start = len(text)
        try:
            with client.beta.messages.stream(
                model=config.model,
                max_tokens=MAX_TOKENS,
                system=[{"type": "text", "text": SYSTEM}],
                tools=TOOLS,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": config.effort},
                cache_control={"type": "ephemeral"},
                **extra,
            ) as stream:
                for event in stream:
                    if event.type == "text":
                        text.append(event.text)
                        yield "text", event.text
                final = stream.get_final_message()
            json_retries = 0
        except ValueError as exc:
            # tool input the SDK could not parse at all: re-issue the turn, bounded, and
            # take back the text this attempt streamed
            json_retries += 1
            if json_retries > 2:
                raise AssistantError("The answer could not be read. Try again.") from exc
            del text[round_start:]
            yield "reset", "".join(text)
            continue
        except anthropic.AnthropicError as exc:
            raise _error(exc, config) from exc

        if final.stop_reason == "refusal":
            # Nothing from a declined turn goes into the history.
            yield "done", Turn("", [], "refusal", "IrereroAI cannot help with that request.")
            return
        if final.stop_reason == "pause_turn":
            reply = {"role": "assistant", "content": assistant_content(final.content)}
            messages.append(reply)
            added.append(reply)
            continue
        reply = {"role": "assistant", "content": assistant_content(final.content)}
        tool_uses = [b for b in final.content if b.type == "tool_use"]
        if final.stop_reason != "tool_use" or not tool_uses:
            notice = None
            if final.stop_reason == "max_tokens":
                notice = "The answer was cut short. Ask a narrower question for the rest."
            if not reply["content"]:
                yield "done", Turn("", [], final.stop_reason, "No answer came back. Try again.")
                return
            added.append(reply)
            yield "done", Turn("".join(text), added, final.stop_reason, notice, used)
            return
        rounds += 1
        if rounds > MAX_TOOL_ROUNDS:
            yield "done", Turn("".join(text), [], "tool_limit",
                               "IrereroAI needed too many lookups. Ask a narrower question.",
                               used)  # fmt: skip
            return
        results = []
        for block in tool_uses:
            used.append(block.name)
            yield "status", STATUS_TEXT.get(block.name, "Looking up the data")
            try:
                content, is_error = (
                    json.dumps(run_tool(block.name, block.input, ctx, tables), default=str),
                    False,
                )
            except (ValueError, PermissionError) as exc:  # facts.NotFound is a ValueError
                content, is_error = str(exc), True
            except Exception as exc:  # a figure that cannot be computed is reported, not fatal
                content, is_error = f"Could not compute this ({type(exc).__name__}).", True
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": content,
                 "is_error": is_error}
            )  # fmt: skip
        if text and not text[-1].endswith(("\n", " ")):
            text.append("\n\n")
            yield "text", "\n\n"
        tool_message = {"role": "user", "content": results}
        messages += [reply, tool_message]
        added += [reply, tool_message]
