"""LangGraph wiring -- the full, guarded shape.

    START -> input_guardrail -> (blocked?) -> blocked_refusal -----------+
                              -> classify_intent                        |
                                   -> (off-topic?) -> refuse_off_topic --+
                                   -> balance_inquiry -------------------+--> output_guardrail -> finalize -> END
                                   -> faq --------------------------------+
                                   -> policy_gate
                                        -> (needs approval?) -> escalate -+
                                        -> refund_request / freeze_card / update_contact -> compose_from_tool_result -+

Every path converges on `output_guardrail` before `finalize` -- there is
exactly one place a response can leave the graph, and exactly one place
that checks it before it does.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes import (
    balance_inquiry_node,
    blocked_refusal_node,
    classify_intent_node,
    compose_from_tool_result_node,
    escalate_node,
    faq_node,
    finalize_node,
    freeze_card_node,
    input_guardrail_node,
    output_guardrail_node,
    policy_gate_node,
    refund_request_node,
    refuse_off_topic_node,
    route_after_classify,
    route_after_input_guardrails,
    route_after_policy_gate,
    update_contact_node,
)
from app.agent.state import GuardianState

RISKY_INTENTS = ("refund_request", "freeze_card", "update_contact")


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(GuardianState)

    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("blocked_refusal", blocked_refusal_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("refuse_off_topic", refuse_off_topic_node)
    graph.add_node("policy_gate", policy_gate_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("balance_inquiry", balance_inquiry_node)
    graph.add_node("refund_request", refund_request_node)
    graph.add_node("freeze_card", freeze_card_node)
    graph.add_node("update_contact", update_contact_node)
    graph.add_node("faq", faq_node)
    graph.add_node("compose_from_tool_result", compose_from_tool_result_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("input_guardrail")
    graph.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrails,
        {"blocked_refusal": "blocked_refusal", "classify_intent": "classify_intent"},
    )
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "refuse_off_topic": "refuse_off_topic",
            "balance_inquiry": "balance_inquiry",
            "faq": "faq",
            "policy_gate": "policy_gate",
        },
    )
    graph.add_conditional_edges(
        "policy_gate",
        route_after_policy_gate,
        {
            "escalate": "escalate",
            "refund_request": "refund_request",
            "freeze_card": "freeze_card",
            "update_contact": "update_contact",
        },
    )
    for node_name in (*RISKY_INTENTS, "balance_inquiry", "escalate"):
        graph.add_edge(node_name, "compose_from_tool_result")

    graph.add_edge("compose_from_tool_result", "output_guardrail")
    graph.add_edge("faq", "output_guardrail")
    graph.add_edge("refuse_off_topic", "output_guardrail")
    graph.add_edge("blocked_refusal", "output_guardrail")
    graph.add_edge("output_guardrail", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def run_agent(account_id: str, user_message: str) -> GuardianState:
    """Single public entry point: one full guarded turn."""
    graph = build_graph()
    result = graph.invoke(GuardianState(account_id=account_id, user_message=user_message))
    return GuardianState.model_validate(result)
