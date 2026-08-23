"""Deterministic business-rule guardrails.

These decide whether a high-risk action needs human approval before it
executes. Deliberately plain code, not an LLM call: an approval threshold is
a business decision with one right answer for a given input, and a model
call would add latency, cost, and a small chance of an inconsistent verdict
for zero benefit. The rule of thumb this project follows: reach for an LLM
guardrail only for judgments that are inherently fuzzy (does this text look
like a jailbreak attempt?); anything expressible as a comparison belongs
here instead, where it's exhaustively unit-testable and always consistent.
"""

from __future__ import annotations


def refund_needs_approval(amount_usd: float, auto_approve_limit_usd: float) -> bool:
    return amount_usd >= auto_approve_limit_usd


def freeze_card_needs_approval(always_needs_approval: bool) -> bool:
    return always_needs_approval


def update_contact_needs_approval(always_needs_approval: bool) -> bool:
    # Changing contact info is a classic account-takeover step (attacker
    # redirects OTPs/statements to their own address) -- so unlike a balance
    # inquiry, this is gated even though "always True" looks trivial today.
    # Kept as a real function (not an inlined constant) so a future,
    # richer rule (e.g. skip approval if the new email was pre-verified)
    # has one place to live without touching call sites.
    return always_needs_approval
