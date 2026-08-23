"""Prompt templates and the fictional bank's ground-truth policy facts.

POLICY_FACTS exists for two reasons: it's what the FAQ node grounds its
answers in, and it's what the output faithfulness guardrail (phase 4) checks
the final response against. Keeping it as one short, explicit block (rather
than "the LLM just knows banking policy") is what makes "did the agent
hallucinate a policy?" an answerable, gradable question instead of a vibe.
"""

from __future__ import annotations

BANK_NAME = "Meridian Bank"

POLICY_FACTS = """\
- Refunds for disputed transactions are issued to the original account; refunds under $250 \
are auto-approved, refunds of $250 or more require manual review before completion.
- A frozen card can be unfrozen at any time by the account holder through the app or by \
calling support; freezing a card never closes the account.
- There is no fee for domestic transfers. Overdrafts incur a flat $35 fee per occurrence.
- Disputes must be filed within 60 days of the transaction date.
- Support is available 24/7 for card-freeze requests; all other requests are handled \
during business hours (8am-8pm local time).
"""

CLASSIFY_INTENT_PROMPT = """You are the intent classifier for {bank_name}'s support assistant.
Classify the user's message into exactly one intent and extract any details it gives you.

User message:
{user_message}

Guidance:
- "balance_inquiry": asking about balance, recent transactions, or account status.
- "refund_request": asking to reverse/dispute a SPECIFIC charge they can point to (usually names \
an amount or transaction). If they're instead asking a general question ABOUT the dispute/refund \
process itself (e.g. "how many days do I have to dispute a charge?"), with no specific charge \
named, that is "faq", not "refund_request".
- "freeze_card": asking to freeze, lock, or block their card.
- "update_contact": asking to change contact info (e.g. email).
- "faq": a general question about policy, fees, dispute windows, or how something works.
- "other": anything not related to this bank's services at all (weather, jokes, poems, stock \
tips, unrelated small talk). If the message isn't actually asking this bank's assistant to do or \
explain something about the user's account or this bank's policies, prefer "other".

Examples:
- "What's my balance?" -> balance_inquiry
- "How many days do I have to dispute a charge?" -> faq (general question, no specific charge named)
- "Refund my $50 charge from TXN-1234." -> refund_request (names a specific charge)
- "What's the weather like today?" -> other
- "Write me a poem about the ocean." -> other
- "Tell me a joke." -> other
- "Give me some stock picks for tomorrow." -> other
"""

FAQ_PROMPT = """You are {bank_name}'s support assistant. Answer the user's question using ONLY \
the policy facts below -- do not invent any fact not stated here. If the facts don't cover the \
question, say you don't have that information rather than guessing.

Output ONLY the reply you would send the customer -- no preamble like "Here's a reply", no \
sign-off, no meta-commentary about what you're doing.

Policy facts:
{policy_facts}

User question:
{user_message}
"""

COMPOSE_RESPONSE_PROMPT = """You are {bank_name}'s support assistant, writing the final reply to \
a customer. Turn the following action result into a short, warm, plain-language reply. State \
only facts present in the result -- do not add numbers, statuses, or promises that aren't there.

Output ONLY the reply you would send the customer -- no preamble like "Here's a reply", no \
sign-off, no meta-commentary about what you're doing.

Action result (JSON):
{tool_result}
"""

OTHER_PROMPT = """You are {bank_name}'s support assistant. Respond to the user's message.

User message:
{user_message}
"""
