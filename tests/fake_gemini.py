"""A local stand-in for the Gemini API, for testing the assistant without an API key.

It speaks the real streaming wire format (`models/{model}:streamGenerateContent?alt=sse`:
server-sent events, each a GenerateContentResponse with text parts, function calls carrying
thought signatures, a finish reason and usage), so the real SDK, its response parsing and the
app's tool loop are all exercised. Its replies are scripted, not generated: a function call
for a question about the data, then a sentence quoting the function response it is sent back.
Markers in a question force failures: [500], [429], [401], [refuse], [long]; [slow] paces the
answer. A wrong key gets Gemini's "API key not valid" (400), a model named missing-* a 404.

It also checks the request rules the assistant must follow and records any break in
`violations`: the system instruction and tool list are identical on every request, each
request repeats the previous one's contents unchanged (append-only), function calls come back
with their thought signatures, and every function response answers a call by name and id.

    python tests/fake_gemini.py 8765      # run it for a manual or browser test
"""

import base64
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from typing import Any

DISTRICTS = ("Muhanga", "Nyagatare", "Gasabo", "Kicukiro", "Rubavu", "Huye", "Bugesera")
PATH = re.compile(r"^/v1beta/models/([^/:]+):streamGenerateContent\?alt=sse$")


class State:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.violations: list[str] = []
        self.attempts = 0
        self.ids = count(1)
        self.lock = threading.Lock()


STATE = State()


def _sse(data: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(data)}\r\n\r\n".encode()


def _question(contents: list[dict[str, Any]]) -> str:
    texts = [p["text"] for p in contents[-1].get("parts", []) if "text" in p]
    return texts[-1] if texts else ""


def _check(body: dict[str, Any], answered: bool) -> None:
    """The append-only rule: a request that continues a conversation must start with an
    earlier answered request's contents, unchanged. The system instruction and tools must
    match that request's. (A declined turn may be dropped: nothing follows it.)"""
    contents = body["contents"]
    with STATE.lock:
        earlier = [r for r in STATE.requests if r["contents"] == contents[: len(r["contents"])]]
        if answered:
            STATE.requests.append(body)
    calls: dict[str, str] = {}
    for c in contents:
        for p in c.get("parts", []):
            if c.get("role") == "model" and "functionCall" in p:
                calls[p["functionCall"].get("id", "")] = p["functionCall"]["name"]
                if not p.get("thoughtSignature"):
                    STATE.violations.append("function call sent back without its signature")
            if "functionResponse" in p:
                r = p["functionResponse"]
                if calls.get(r.get("id", "")) != r["name"]:
                    STATE.violations.append("function response does not answer a call")
    if len(contents) == 1:
        return  # a new conversation
    if not earlier:
        STATE.violations.append("earlier messages were edited, not appended")
        return
    parent = max(earlier, key=lambda r: len(r["contents"]))
    if parent["systemInstruction"] != body["systemInstruction"]:
        STATE.violations.append("system prompt changed within a conversation")
    if parent["tools"] != body["tools"]:
        STATE.violations.append("tool list changed within a conversation")


def _plan(body: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """(model parts, finish reason) for this request; finish None means a blocked prompt."""
    contents = body["contents"]
    signature = base64.b64encode(f"sig-{next(STATE.ids)}".encode()).decode()  # bytes, as sent
    responses = [p["functionResponse"] for p in contents[-1]["parts"] if "functionResponse" in p]
    if responses:
        response = responses[0]["response"]
        if "error" in response:
            return [{"text": f"That is not available: {response['error']}"}], "STOP"
        return [{"text": _summary(response["output"]), "thoughtSignature": signature}], "STOP"
    q = _question(contents).lower()
    if "[refuse]" in q:
        return [], None
    if "[long]" in q:
        return [{"text": "This answer is long and gets cut"}], "MAX_TOKENS"
    if "scope" in q or ("simulated" in q and "mean" in q):
        return [
            {"text": "The scope is formal pre-primary: children aged 3 to 5 attending nursery "
             "or pre-primary school. Simulated values are stand-ins.",
             "thoughtSignature": signature},
        ], "STOP"  # fmt: skip
    if "sector" in q:
        call = {"name": "get_sector", "args": {"district": "Muhanga", "sector": "Cyeza"}}
    elif any(d.lower() in q for d in DISTRICTS):
        d = next(d for d in DISTRICTS if d.lower() in q)
        call = {"name": "get_district", "args": {"district": d}}
    elif "priorit" in q or "compare" in q or "which district" in q:
        call = {"name": "compare_districts", "args": {"sort_by": "places_needed"}}
    elif "real" in q or ("data" in q and "source" in q):
        call = {"name": "get_data_status"}  # no arguments: Gemini sends no args
    else:
        call = {"name": "get_overview", "args": {}}
    return [
        {"text": "Let me check the dashboard."},
        {"functionCall": {"id": f"call_{next(STATE.ids)}", **call}, "thoughtSignature": signature},
    ], "STOP"


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

    def _error(self, code: int, status: str, message: str, details: list | None = None) -> None:
        error = {"code": code, "message": message, "status": status}
        if details:
            error["details"] = details
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": error}).encode())

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
        STATE.attempts += 1
        match = PATH.match(self.path)
        if not match:
            return self._error(404, "NOT_FOUND", "no such endpoint")
        if self.headers.get("x-goog-api-key") != "test-key":
            return self._error(
                400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key."
            )
        model = match.group(1)
        if model.startswith("missing-"):
            return self._error(404, "NOT_FOUND", f"models/{model} is not found")
        body["model"] = model
        q = _question(body["contents"]).lower()
        if "[401]" in q:
            return self._error(401, "UNAUTHENTICATED", "Request had invalid credentials.")
        if "[429]" in q:
            retry = {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "19.2s"}
            return self._error(
                429, "RESOURCE_EXHAUSTED", "You exceeded your current quota.", [retry]
            )
        if "[500]" in q:
            return self._error(500, "INTERNAL", "An internal error has occurred.")
        parts, finish = _plan(body)
        _check(body, answered=finish is not None)
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.end_headers()
        w = self.wfile.write
        usage = {"promptTokenCount": 50, "candidatesTokenCount": 30, "totalTokenCount": 80}
        if finish is None:
            w(
                _sse(
                    {
                        "promptFeedback": {"blockReason": "PROHIBITED_CONTENT"},
                        "usageMetadata": usage,
                    }
                )
            )
            self.wfile.flush()
            return
        slow = "[slow]" in json.dumps(body["contents"][-3:])  # pace like a real model
        chunks: list[dict[str, Any]] = []
        for part in parts:
            if "text" not in part:
                chunks.append(part)
                continue
            for i, word in enumerate(re.findall(r"\S+\s*", part["text"])):
                piece = {"text": word}
                if i == 0 and "thoughtSignature" in part:
                    piece["thoughtSignature"] = part["thoughtSignature"]
                chunks.append(piece)
        for i, piece in enumerate(chunks):
            if slow:
                time.sleep(0.25)
                self.wfile.flush()
            candidate: dict[str, Any] = {"content": {"role": "model", "parts": [piece]}, "index": 0}
            if i == len(chunks) - 1:
                candidate["finishReason"] = finish
            w(_sse({"candidates": [candidate], "usageMetadata": usage, "modelVersion": model}))
        self.wfile.flush()


def serve(port: int = 0) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"fake Gemini API on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if STATE.violations:
            print("VIOLATIONS:", *STATE.violations, sep="\n- ")
