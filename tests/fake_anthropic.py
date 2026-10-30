"""A local stand-in for the Messages API, for testing the assistant without an API key.

It speaks the real streaming wire format (server-sent events: message_start, content blocks
with text, thinking signatures and tool_use input deltas, message_delta, message_stop), so the
real SDK, its stream accumulator and the app's tool loop are all exercised. Its replies are
scripted, not generated: a tool call for a question about the data, then a sentence quoting
the tool result it is sent back. Markers in a question force failures: [500], [429], [401],
[refuse], [long], [cut-tool] (cut off inside a tool call); [slow] paces the answer. A model
named missing-* gets a 404.

It also checks the request rules the assistant must follow and records any break in
`violations`: the system prompt and tool list are identical on every request, each request
repeats the previous one's messages unchanged (append-only), and thinking blocks come back with
their signatures, and every tool call is answered by a tool result in the next message.

    python tests/fake_anthropic.py 8765      # run it for a manual or browser test
"""

import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from typing import Any

DISTRICTS = ("Muhanga", "Nyagatare", "Gasabo", "Kicukiro", "Rubavu", "Huye", "Bugesera")


class State:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.violations: list[str] = []
        self.ids = count(1)
        self.lock = threading.Lock()


STATE = State()


def _sse(kind: str, data: dict[str, Any]) -> bytes:
    return f"event: {kind}\ndata: {json.dumps(data)}\n\n".encode()


def _question(messages: list[dict[str, Any]]) -> str:
    last = messages[-1]
    blocks = last["content"] if isinstance(last["content"], list) else [last["content"]]
    texts = [b["text"] for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
    return texts[-1] if texts else ""


def _check(body: dict[str, Any], answered: bool) -> None:
    """The append-only rule: a request that continues a conversation must start with an
    earlier answered request's messages, unchanged. The system prompt and tools must match
    that request's. (A declined turn may be dropped: nothing follows it, no thinking.)"""
    messages = body["messages"]
    with STATE.lock:
        earlier = [r for r in STATE.requests if r["messages"] == messages[: len(r["messages"])]]
        if answered:
            STATE.requests.append(body)
    for m in messages:
        if m["role"] == "assistant":
            for b in m["content"]:
                if b.get("type") == "thinking" and not b.get("signature"):
                    STATE.violations.append("thinking block sent back without its signature")
    for i, m in enumerate(messages):  # the API rejects a tool call left unanswered
        calls = [b["id"] for b in m["content"] if m["role"] == "assistant"
                 and isinstance(b, dict) and b.get("type") == "tool_use"]  # fmt: skip
        if not calls:
            continue
        after = messages[i + 1]["content"] if i + 1 < len(messages) else []
        answered = {b.get("tool_use_id") for b in after if isinstance(b, dict)}
        if i + 1 < len(messages) and not set(calls) <= answered:
            STATE.violations.append("a tool call was not answered in the next message")
    if len(messages) == 1:
        return  # a new conversation
    if not earlier:
        STATE.violations.append("earlier messages were edited, not appended")
        return
    parent = max(earlier, key=lambda r: len(r["messages"]))
    if parent["system"] != body["system"]:
        STATE.violations.append("system prompt changed within a conversation")
    if parent["tools"] != body["tools"]:
        STATE.violations.append("tool list changed within a conversation")


def _plan(body: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    """(content blocks, stop_reason) for this request."""
    messages = body["messages"]
    last = messages[-1]
    thinking = {"type": "thinking", "thinking": "", "signature": f"sig-{next(STATE.ids)}"}
    results = [b for b in last["content"] if isinstance(b, dict) and b.get("type") == "tool_result"]
    if results:
        r = results[0]
        if r.get("is_error"):
            return [thinking, {"type": "text", "text": f"That is not available: {r['content']}"}], (
                "end_turn"
            )
        data = json.loads(r["content"])
        return [thinking, {"type": "text", "text": _summary(data)}], "end_turn"
    q = _question(messages).lower()
    if "[refuse]" in q:
        return [], "refusal"
    if "[cut-tool]" in q:
        tool = {"type": "tool_use", "id": f"toolu_{next(STATE.ids)}", "name": "get_overview",
                "input": {}}  # fmt: skip
        return [thinking, {"type": "text", "text": "Let me check."}, tool], "max_tokens"
    if "[long]" in q:
        return [thinking, {"type": "text", "text": "This answer is long and gets cut"}], (
            "max_tokens"
        )
    if "scope" in q or ("simulated" in q and "mean" in q):
        return [
            thinking,
            {"type": "text", "text": "The scope is formal pre-primary: children aged 3 to 5 "
             "attending nursery or pre-primary school. Simulated values are stand-ins."},
        ], "end_turn"  # fmt: skip
    if "sector" in q:
        call = {"name": "get_sector", "input": {"district": "Muhanga", "sector": "Cyeza"}}
    elif any(d.lower() in q for d in DISTRICTS):
        d = next(d for d in DISTRICTS if d.lower() in q)
        call = {"name": "get_district", "input": {"district": d}}
    elif "priorit" in q or "compare" in q or "which district" in q:
        call = {"name": "compare_districts", "input": {"sort_by": "places_needed"}}
    elif "real" in q or ("data" in q and "source" in q):
        call = {"name": "get_data_status", "input": {}}
    else:
        call = {"name": "get_overview", "input": {}}
    tool = {"type": "tool_use", "id": f"toolu_{next(STATE.ids)}", **call}
    return [thinking, {"type": "text", "text": "Let me check the dashboard."}, tool], "tool_use"


def _summary(data: dict[str, Any]) -> str:
    """A sentence quoting the figures the tool returned, so a test can see them arrive."""
    if "estimate_2026" in data and "national_trend" in data:
        e, n = data["estimate_2026"], data["national_trend"]
        return (
            f"In {data['area']}, {e['attending_pre_primary_pct']}% of children aged 3-5 attend "
            f"pre-primary ({e['status']}). The national trend reaches "
            f"{n['projected_2028/29_pct']}% by 2028/29, {n['status_vs_target']}."
        )
    if "districts" in data:
        top = data["districts"][0]
        return (
            f"By places needed, {top['district']} comes first with {top['places_needed']:,} "
            f"places ({data['status']})."
        )
    if "priority" in data or "trend" in data:
        e = data["estimate_2026"]
        return (
            f"{data['district']} needs {e['places_needed']:,} places to reach "
            f"{data['target_attendance_pct']:g}% ({e['status']})."
        )
    if "sector" in data:
        return f"{data['sector']}: main bottleneck {data['main_bottleneck']} ({data['status']})."
    if "real_files" in data:
        return f"{len(data['real_files'])} dataset(s) are real files; the rest are simulated."
    return "Done."


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        pass

    def _error(self, status: int, kind: str, message: str, headers: dict[str, str]) -> None:
        body = json.dumps({"type": "error", "error": {"type": kind, "message": message}})
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("x-should-retry", "false")
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self) -> None:
        """/_violations: the append-only rule breaks seen so far (for browser test runs)."""
        body = json.dumps({"requests": len(STATE.requests), "violations": STATE.violations})
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length))
        if not re.match(r"^/v1/messages(\?|$)", self.path):
            return self._error(404, "not_found_error", "no such endpoint", {})
        key = self.headers.get("x-api-key") or self.headers.get("authorization", "").removeprefix(
            "Bearer "
        )
        if key != "test-key":
            return self._error(401, "authentication_error", "invalid x-api-key", {})
        if body["model"].startswith("missing-"):
            return self._error(404, "not_found_error", f"model: {body['model']}", {})
        q = _question(body["messages"]).lower()
        if "[401]" in q:
            return self._error(401, "authentication_error", "invalid x-api-key", {})
        if "[429]" in q:
            return self._error(429, "rate_limit_error", "rate limited", {"retry-after": "20"})
        if "[500]" in q:
            return self._error(500, "api_error", "internal error", {})
        content, stop = _plan(body)
        _check(body, answered=stop != "refusal")
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.end_headers()
        w = self.wfile.write
        w(_sse("message_start", {"type": "message_start", "message": {
            "id": f"msg_{next(STATE.ids)}", "type": "message", "role": "assistant",
            "model": body["model"], "content": [], "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 50, "output_tokens": 1}}}))  # fmt: skip
        for i, block in enumerate(content):
            if block["type"] == "thinking":
                w(
                    _sse(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": i,
                            "content_block": {"type": "thinking", "thinking": "", "signature": ""},
                        },
                    )
                )
                w(
                    _sse(
                        "content_block_delta",
                        {
                            "type": "content_block_delta",
                            "index": i,
                            "delta": {"type": "signature_delta", "signature": block["signature"]},
                        },
                    )
                )
            elif block["type"] == "text":
                w(
                    _sse(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": i,
                            "content_block": {"type": "text", "text": ""},
                        },
                    )
                )
                slow = "[slow]" in json.dumps(body["messages"][-3:])  # pace like a real model
                for word in re.findall(r"\S+\s*", block["text"]):
                    if slow:
                        time.sleep(0.25)
                        self.wfile.flush()
                    w(
                        _sse(
                            "content_block_delta",
                            {
                                "type": "content_block_delta",
                                "index": i,
                                "delta": {"type": "text_delta", "text": word},
                            },
                        )
                    )
            else:
                w(
                    _sse(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": i,
                            "content_block": {
                                "type": "tool_use",
                                "id": block["id"],
                                "name": block["name"],
                                "input": {},
                            },
                        },
                    )
                )
                w(
                    _sse(
                        "content_block_delta",
                        {
                            "type": "content_block_delta",
                            "index": i,
                            "delta": {
                                "type": "input_json_delta",
                                "partial_json": json.dumps(block["input"]),
                            },
                        },
                    )
                )
            w(_sse("content_block_stop", {"type": "content_block_stop", "index": i}))
        w(
            _sse(
                "message_delta",
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": stop, "stop_sequence": None},
                    "usage": {"output_tokens": 30},
                },
            )
        )
        w(_sse("message_stop", {"type": "message_stop"}))  # fmt: skip
        self.wfile.flush()


def serve(port: int = 0) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"fake Messages API on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if STATE.violations:
            print("VIOLATIONS:", *STATE.violations, sep="\n- ")
