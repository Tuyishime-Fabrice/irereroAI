"""The assistant behind "Why this suggestion?".

Phase 1 answers from templates only. Any provider may answer only from platform data that the
caller passes in, and must name the source tables it used. A language-model provider is a
Phase 2 addition behind this same interface; until it exists, setting an API key changes nothing.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from irerero_engine.types import SourceRef

QUESTIONS = ("why", "sources", "uncertainty", "who_decides")

KEYWORDS = {
    "why": ("why", "reason", "kubera", "impamvu"),
    "sources": ("source", "data", "where", "isoko", "amakuru"),
    "uncertainty": ("sure", "range", "confidence", "uncertain", "interval", "ukuri", "intera"),
    "who_decides": ("decide", "approve", "automatic", "human", "ufata", "wemeza"),
}


@dataclass(frozen=True)
class AssistantContext:
    subject: str  # e.g. "Build a new centre at Cyumba village site A"
    explanation_en: str
    explanation_rw: str
    range_en: str
    range_rw: str
    sources: Sequence[SourceRef]


@dataclass(frozen=True)
class Answer:
    question: str
    text: str
    tables: tuple[str, ...]
    provider: str


class AssistantProvider(Protocol):
    name: str

    def answer(self, question: str, language: str, context: AssistantContext) -> Answer: ...


def classify(question: str) -> str | None:
    """Map a typed question to one of the supported questions, or None."""
    lowered = question.lower()
    if lowered in QUESTIONS:
        return lowered
    for key, words in KEYWORDS.items():
        if any(word in lowered for word in words):
            return key
    return None


class TemplateAssistant:
    name = "templates"

    def answer(self, question: str, language: str, context: AssistantContext) -> Answer:
        key = classify(question)
        rw = language == "rw"
        tables = tuple(sorted({s.table for s in context.sources}))
        if key == "why":
            text = context.explanation_rw if rw else context.explanation_en
        elif key == "sources":
            listed = "; ".join(
                f"{s.source} ({s.reference_year}, {s.origin}) in {s.table}" for s in context.sources
            )
            text = (
                f"Iyi nama ishingiye kuri aya makuru: {listed}."
                if rw
                else f"This suggestion uses: {listed}."
            )
        elif key == "uncertainty":
            text = context.range_rw if rw else context.range_en
        elif key == "who_decides":
            text = (
                "Iyi ni inama gusa. Umuntu ni we wemeza, ahindura cyangwa yanga, kandi "
                "icyemezo cyose kibikwa mu gitabo cy'igenzura. Nta kintu gikorwa mu buryo bwikora."
                if rw
                else "This is a suggestion only. A person approves, edits or rejects it, every "
                "decision is written to the audit log, and nothing happens automatically."
            )
            tables = ("audit_log", "decision")
        else:
            text = (
                "Nshobora gusubiza ibi bibazo: kubera iki, amakuru yakoreshejwe, ukuri "
                "kw'imibare, n'ufata icyemezo."
                if rw
                else "I can answer: why this suggestion, which data it uses, how sure it is, "
                "and who decides."
            )
            tables = ()
        return Answer(key or "unknown", text, tables, self.name)


def make_assistant(api_key: str | None) -> AssistantProvider:
    """Templates in Phase 1, whatever the key. The Phase 2 provider plugs in here."""
    del api_key
    return TemplateAssistant()
