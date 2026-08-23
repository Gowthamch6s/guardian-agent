"""Graph state schema.

A pydantic model (not a bare TypedDict) so every node's return value is
validated on the way in -- a malformed field from a bad LLM parse fails loud
at the node boundary instead of silently drifting through the rest of the
graph. This is a linear-ish graph (no cycles, no concurrent branches writing
the same field), so plain field replacement is enough; no reducer/Annotated
machinery needed the way AgentFlow Studio's cyclic graph requires it.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class GuardianState(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    # --- input ---
    account_id: str
    user_message: str

    # --- classification ---
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    transaction_id: Optional[str] = None
    amount_usd: Optional[float] = None
    new_contact_email: Optional[str] = None

    # --- guardrail bookkeeping (populated starting phase 3/4) ---
    blocked: bool = False
    block_reason: Optional[str] = None
    guardrail_trace: list[dict[str, Any]] = Field(default_factory=list)

    # --- action execution ---
    requires_human_approval: bool = False
    tool_result: Optional[dict[str, Any]] = None
    escalation: Optional[dict[str, Any]] = None

    # --- output ---
    draft_response: Optional[str] = None
    final_response: Optional[str] = None
