"""Output-side guardrails: run on the agent's drafted response before it's sent.

Faithfulness scoring reuses `agent_observability_kit.eval.LLMJudge` -- the
same class the offline eval harness uses -- but here as a *live* runtime
guardrail rather than an offline scorer. It's an independent LLM call scoring
the response against the actual grounding text (tool result / policy facts),
never the same call that generated the response: an agent asked "was your
own answer good?" is a biased witness, so the judge has to be a separate
voice. This is the one guardrail in the project that's inherently fuzzy
enough to warrant an LLM rather than a rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from agent_observability_kit.eval import LLMJudge

from app.guardrails.patterns import mask_pii
from app.guardrails.types import GuardrailFinding

FAITHFULNESS_BLOCK_THRESHOLD = 0.4

_BANNED_OUTPUT_PATTERNS = [
    re.compile(r"\b(idiot|stupid|shut up)\b", re.I),
]

SAFE_FALLBACK_RESPONSE = (
    "I want to double-check those details before sharing them. I've flagged this for a "
    "specialist to follow up with you directly."
)


def scrub_pii_from_response(text: str) -> tuple[str, GuardrailFinding]:
    return mask_pii(text, "output_pii_scrub", card_mask=lambda last4: f"•••• {last4}")


def toxicity_check(text: str) -> GuardrailFinding:
    for pattern in _BANNED_OUTPUT_PATTERNS:
        if pattern.search(text):
            return GuardrailFinding("toxicity_heuristic", True, f"matched: {pattern.pattern}")
    return GuardrailFinding("toxicity_heuristic", False)


@dataclass
class FaithfulnessResult:
    finding: GuardrailFinding
    score: float


def faithfulness_check(
    grounding_text: str,
    response_text: str,
    call_llm: Callable[[str], str],
    threshold: float = FAITHFULNESS_BLOCK_THRESHOLD,
) -> FaithfulnessResult:
    judge = LLMJudge(call_llm=call_llm, criteria=["faithfulness"])
    result = judge.score(input_text=grounding_text, output_text=response_text)
    score = result.scores.get("faithfulness", 0.0)
    fired = score < threshold
    finding = GuardrailFinding("faithfulness_judge", fired, f"score={score:.2f}")
    return FaithfulnessResult(finding=finding, score=score)
