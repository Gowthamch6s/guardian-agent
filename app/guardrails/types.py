"""Shared result type every guardrail returns.

One shape for every guardrail (input, output, deterministic, or LLM-based)
so the graph's trace log, the eval harness, and the Streamlit UI can all
consume guardrail results the same way without knowing which guardrail
produced them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GuardrailFinding:
    guardrail: str
    fired: bool
    detail: str = ""
