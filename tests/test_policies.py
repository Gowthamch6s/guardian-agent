from app.guardrails.policies import (
    freeze_card_needs_approval,
    refund_needs_approval,
    update_contact_needs_approval,
)


def test_refund_under_limit_is_auto_approved():
    assert refund_needs_approval(amount_usd=100.0, auto_approve_limit_usd=250.0) is False


def test_refund_at_or_over_limit_needs_approval():
    assert refund_needs_approval(amount_usd=250.0, auto_approve_limit_usd=250.0) is True
    assert refund_needs_approval(amount_usd=999.0, auto_approve_limit_usd=250.0) is True


def test_freeze_card_follows_the_configured_flag():
    assert freeze_card_needs_approval(always_needs_approval=True) is True
    assert freeze_card_needs_approval(always_needs_approval=False) is False


def test_update_contact_follows_the_configured_flag():
    assert update_contact_needs_approval(always_needs_approval=True) is True
    assert update_contact_needs_approval(always_needs_approval=False) is False
