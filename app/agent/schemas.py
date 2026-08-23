"""Pydantic schemas for structured LLM output.

Every LLM call in this project that needs a *decision* (not free text) goes
through `.with_structured_output(SomeSchema)` rather than parsing prose --
same pattern used in market-research-agent and AgentFlow Studio. This is
what makes routing and guardrail decisions reliable enough to build a graph
edge on: a raw text reply like "sure, I'll refund that" is not something you
can safely branch control flow on, but `intent="refund_request"` is.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Intent = Literal[
    "balance_inquiry",
    "refund_request",
    "freeze_card",
    "update_contact",
    "faq",
    "other",
]


class IntentClassification(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    transaction_id: Optional[str] = Field(
        default=None, description="Only for refund_request, if the user named one."
    )
    amount_usd: Optional[float] = Field(
        default=None, description="Only for refund_request, if the user named an amount."
    )
    new_contact_email: Optional[str] = Field(
        default=None, description="Only for update_contact, if the user gave a new email."
    )
