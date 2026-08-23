"""Turns `GuardrailFinding`s into the plain-dict trace entries every
consumer (graph state, eval harness, Streamlit UI) shares one shape for.

A free function rather than a state method: nodes build a new list and
return it as part of their dict update (LangGraph's functional-update
convention, matching how every other field in GuardianState is set) instead
of mutating shared state in place.
"""

from __future__ import annotations

from app.guardrails.types import GuardrailFinding


def append_findings(existing: list[dict], *findings: GuardrailFinding) -> list[dict]:
    return existing + [
        {"guardrail": f.guardrail, "outcome": "fired" if f.fired else "clear", "detail": f.detail}
        for f in findings
    ]
