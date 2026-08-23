"""Shared PII regex patterns and masking, used on both the input and output side.

Kept in one place because the two sides differ only in *how* a caught card
number gets displayed back (a distinct redaction tag on input vs. a
last-4-digits mask on output) and in the guardrail name attached to the
finding -- the detection logic itself must not drift between the two call
sites, or "we scrub SSNs" would quietly mean two different regexes.
"""

from __future__ import annotations

import re
from typing import Callable

from app.guardrails.types import GuardrailFinding

SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def mask_pii(text: str, guardrail_name: str, card_mask: Callable[[str], str]) -> tuple[str, GuardrailFinding]:
    """Replace SSN-/card-like sequences in `text`. `card_mask(last_four_digits)`
    controls the replacement shown for a caught card number."""
    found: list[str] = []

    def _mask_ssn(match: re.Match) -> str:
        found.append("ssn")
        return "[REDACTED_SSN]"

    def _mask_card(match: re.Match) -> str:
        digits = re.sub(r"[ -]", "", match.group(0))
        if len(digits) < 13:
            return match.group(0)
        found.append("card_number")
        return card_mask(digits[-4:])

    scrubbed = SSN_PATTERN.sub(_mask_ssn, text)
    scrubbed = CARD_PATTERN.sub(_mask_card, scrubbed)
    finding = GuardrailFinding(guardrail_name, bool(found), f"redacted: {found}" if found else "")
    return scrubbed, finding
