"""Graph nodes.

Guardrails are inserted as their own nodes rather than folded into the nodes
that classify/act/respond, so each one is independently visible in the
guardrail trace and independently swappable (e.g. tightening the
faithfulness threshold later touches one node, not the whole graph).
"""

from __future__ import annotations

import json

from app.agent import tools
from app.agent.llm import call_llm_text, get_llm
from app.agent.prompts import (
    BANK_NAME,
    CLASSIFY_INTENT_PROMPT,
    COMPOSE_RESPONSE_PROMPT,
    FAQ_PROMPT,
    POLICY_FACTS,
)
from app.agent.schemas import IntentClassification
from app.agent.state import GuardianState
from app.config import get_settings
from app.guardrails import input_guardrails, output_guardrails, policies
from app.guardrails.trace import append_findings
from app.guardrails.types import GuardrailFinding

OFF_TOPIC_RESPONSE = (
    f"I can help with account balances, refunds, card freezes, and contact updates for "
    f"{BANK_NAME}. I'm not able to help with that request."
)
GENERIC_BLOCKED_RESPONSE = (
    "I can't process that request as written. If you'd like help with your account, "
    "please rephrase your question."
)


# --- input guardrails -------------------------------------------------------


def input_guardrail_node(state: GuardianState) -> dict:
    scrubbed_message, pii_finding = input_guardrails.scrub_pii(state.user_message)

    heuristic_finding = input_guardrails.heuristic_injection_check(scrubbed_message)
    if heuristic_finding.fired:
        llm_finding = GuardrailFinding("llm_injection_classifier", False, "skipped: heuristic already blocked")
    else:
        llm_finding = input_guardrails.llm_injection_check(scrubbed_message, call_llm=call_llm_text)

    blocked = heuristic_finding.fired or llm_finding.fired
    return {
        "user_message": scrubbed_message,
        "blocked": blocked,
        "block_reason": "prompt_injection" if blocked else None,
        "guardrail_trace": append_findings(state.guardrail_trace, pii_finding, heuristic_finding, llm_finding),
    }


def route_after_input_guardrails(state: GuardianState) -> str:
    return "blocked_refusal" if state.blocked else "classify_intent"


def blocked_refusal_node(state: GuardianState) -> dict:
    return {"draft_response": GENERIC_BLOCKED_RESPONSE}


# --- classification ----------------------------------------------------------


def classify_intent_node(state: GuardianState) -> dict:
    structured_llm = get_llm(temperature=0).with_structured_output(IntentClassification)
    prompt = CLASSIFY_INTENT_PROMPT.format(bank_name=BANK_NAME, user_message=state.user_message)
    result: IntentClassification = structured_llm.invoke(prompt)
    return {
        "intent": result.intent,
        "intent_confidence": result.confidence,
        "transaction_id": result.transaction_id,
        "amount_usd": result.amount_usd,
        "new_contact_email": result.new_contact_email,
    }


def route_after_classify(state: GuardianState) -> str:
    topic_finding = input_guardrails.topic_scope_check(state.intent or "other")
    if topic_finding.fired:
        return "refuse_off_topic"
    if state.intent in ("refund_request", "freeze_card", "update_contact"):
        return "policy_gate"
    return state.intent or "refuse_off_topic"


def refuse_off_topic_node(state: GuardianState) -> dict:
    finding = input_guardrails.topic_scope_check(state.intent or "other")
    return {
        "blocked": True,
        "block_reason": "off_topic",
        "draft_response": OFF_TOPIC_RESPONSE,
        "guardrail_trace": append_findings(state.guardrail_trace, finding),
    }


# --- action-authorization policy gate ----------------------------------------


def policy_gate_node(state: GuardianState) -> dict:
    settings = get_settings()

    if state.intent == "refund_request":
        requires_approval = policies.refund_needs_approval(
            amount_usd=state.amount_usd or 0.0,
            auto_approve_limit_usd=settings.refund_auto_approve_limit_usd,
        )
        detail = f"refund ${state.amount_usd} vs limit ${settings.refund_auto_approve_limit_usd}"
    elif state.intent == "freeze_card":
        requires_approval = policies.freeze_card_needs_approval(settings.card_freeze_always_needs_approval)
        detail = "card freeze always requires approval" if requires_approval else ""
    else:  # update_contact
        requires_approval = policies.update_contact_needs_approval(
            settings.update_contact_always_needs_approval
        )
        detail = "contact changes always require approval" if requires_approval else ""

    finding = GuardrailFinding("policy_gate", requires_approval, detail)
    return {
        "requires_human_approval": requires_approval,
        "guardrail_trace": append_findings(state.guardrail_trace, finding),
    }


def route_after_policy_gate(state: GuardianState) -> str:
    return "escalate" if state.requires_human_approval else state.intent


def escalate_node(state: GuardianState) -> dict:
    result = tools.escalate_to_human(
        reason=f"{state.intent} requires manual approval",
        payload={
            "account_id": state.account_id,
            "intent": state.intent,
            "transaction_id": state.transaction_id,
            "amount_usd": state.amount_usd,
            "new_contact_email": state.new_contact_email,
        },
    )
    return {"tool_result": result, "escalation": result}


# --- tool execution -----------------------------------------------------------


def balance_inquiry_node(state: GuardianState) -> dict:
    try:
        result = tools.get_account_summary(state.account_id)
    except tools.AccountNotFoundError:
        result = {"status": "error", "message": f"No account found for {state.account_id}."}
    return {"tool_result": result}


def refund_request_node(state: GuardianState) -> dict:
    if not state.transaction_id or state.amount_usd is None:
        return {"tool_result": {"status": "error", "message": "Missing transaction_id or amount for refund."}}
    try:
        result = tools.initiate_refund(state.account_id, state.transaction_id, state.amount_usd)
    except (tools.AccountNotFoundError, tools.TransactionNotFoundError) as exc:
        result = {"status": "error", "message": f"Could not process refund: {exc}"}
    return {"tool_result": result}


def freeze_card_node(state: GuardianState) -> dict:
    try:
        result = tools.freeze_card(state.account_id)
    except tools.AccountNotFoundError:
        result = {"status": "error", "message": f"No account found for {state.account_id}."}
    return {"tool_result": result}


def update_contact_node(state: GuardianState) -> dict:
    if not state.new_contact_email:
        return {"tool_result": {"status": "error", "message": "No new contact email was given."}}
    try:
        result = tools.update_contact_info(state.account_id, "contact_email", state.new_contact_email)
    except tools.AccountNotFoundError:
        result = {"status": "error", "message": f"No account found for {state.account_id}."}
    return {"tool_result": result}


def faq_node(state: GuardianState) -> dict:
    prompt = FAQ_PROMPT.format(bank_name=BANK_NAME, policy_facts=POLICY_FACTS, user_message=state.user_message)
    text = get_llm(temperature=0.2).invoke(prompt).content
    return {"draft_response": text}


def compose_from_tool_result_node(state: GuardianState) -> dict:
    prompt = COMPOSE_RESPONSE_PROMPT.format(bank_name=BANK_NAME, tool_result=json.dumps(state.tool_result))
    text = get_llm(temperature=0.2).invoke(prompt).content
    return {"draft_response": text}


# --- output guardrails --------------------------------------------------------


def output_guardrail_node(state: GuardianState) -> dict:
    if state.blocked:
        # Already refused upstream (injection / off-topic) -- nothing to
        # ground or scrub, the canned refusal text carries no risk.
        return {}

    grounding_text = (
        json.dumps(state.tool_result) if state.tool_result is not None else POLICY_FACTS
    )
    response_text = state.draft_response or ""

    faithfulness = output_guardrails.faithfulness_check(grounding_text, response_text, call_llm=call_llm_text)
    findings = [faithfulness.finding]

    if faithfulness.finding.fired:
        response_text = output_guardrails.SAFE_FALLBACK_RESPONSE
        blocked, block_reason = True, "low_faithfulness"
    else:
        blocked, block_reason = state.blocked, state.block_reason

    toxicity = output_guardrails.toxicity_check(response_text)
    findings.append(toxicity)
    if toxicity.fired:
        response_text = output_guardrails.SAFE_FALLBACK_RESPONSE
        blocked, block_reason = True, "toxic_output"

    response_text, pii_finding = output_guardrails.scrub_pii_from_response(response_text)
    findings.append(pii_finding)

    return {
        "draft_response": response_text,
        "blocked": blocked,
        "block_reason": block_reason,
        "guardrail_trace": append_findings(state.guardrail_trace, *findings),
    }


def finalize_node(state: GuardianState) -> dict:
    return {"final_response": state.draft_response}
