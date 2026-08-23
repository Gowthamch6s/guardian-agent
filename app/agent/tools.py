"""MockBank: an in-memory fake bank the agent's tools act on.

Tools are deliberately "dumb" -- they perform the requested action and
return a result. They do not decide whether an action is *allowed*; that
judgment belongs to app/guardrails/policies.py, which runs before a tool
that has real-world consequences gets invoked. Keeping "can this happen" out
of "how this happens" is what lets the guardrail layer be tested (and
reasoned about) independently of the tool implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Transaction:
    id: str
    description: str
    amount_usd: float


@dataclass
class Account:
    account_id: str
    owner_name: str
    balance_usd: float
    card_status: str  # "active" | "frozen"
    contact_email: str
    transactions: list[Transaction] = field(default_factory=list)


_ACCOUNTS: dict[str, Account] = {
    "ACC-1001": Account(
        account_id="ACC-1001",
        owner_name="Jordan Lee",
        balance_usd=4213.55,
        card_status="active",
        contact_email="jordan.lee@example.com",
        transactions=[
            Transaction("TXN-9001", "Coffee Shop", 5.75),
            Transaction("TXN-9002", "Duplicate Grocery Charge", 84.20),
            Transaction("TXN-9003", "Streaming Subscription", 14.99),
        ],
    ),
    "ACC-1002": Account(
        account_id="ACC-1002",
        owner_name="Priya Nair",
        balance_usd=812.10,
        card_status="active",
        contact_email="priya.nair@example.com",
        transactions=[
            Transaction("TXN-9101", "Electronics Store", 899.00),
            Transaction("TXN-9102", "Gas Station", 42.10),
        ],
    ),
}


class AccountNotFoundError(Exception):
    pass


class TransactionNotFoundError(Exception):
    pass


def _get_account(account_id: str) -> Account:
    account = _ACCOUNTS.get(account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return account


def get_account_summary(account_id: str) -> dict:
    account = _get_account(account_id)
    return {
        "account_id": account.account_id,
        "owner_name": account.owner_name,
        "balance_usd": account.balance_usd,
        "card_status": account.card_status,
        "recent_transactions": [
            {"id": t.id, "description": t.description, "amount_usd": t.amount_usd}
            for t in account.transactions
        ],
    }


def initiate_refund(account_id: str, transaction_id: str, amount_usd: float) -> dict:
    account = _get_account(account_id)
    if not any(t.id == transaction_id for t in account.transactions):
        raise TransactionNotFoundError(transaction_id)
    account.balance_usd += amount_usd
    return {
        "status": "completed",
        "account_id": account_id,
        "transaction_id": transaction_id,
        "refunded_usd": amount_usd,
        "new_balance_usd": account.balance_usd,
    }


def freeze_card(account_id: str) -> dict:
    account = _get_account(account_id)
    account.card_status = "frozen"
    return {"status": "completed", "account_id": account_id, "card_status": "frozen"}


def update_contact_info(account_id: str, field_name: str, new_value: str) -> dict:
    account = _get_account(account_id)
    if field_name != "contact_email":
        raise ValueError(f"Unsupported field: {field_name}")
    account.contact_email = new_value
    return {"status": "completed", "account_id": account_id, "contact_email": new_value}


_ESCALATION_COUNTER = {"next_id": 1}


def escalate_to_human(reason: str, payload: Optional[dict] = None) -> dict:
    ticket_id = f"ESC-{_ESCALATION_COUNTER['next_id']:04d}"
    _ESCALATION_COUNTER["next_id"] += 1
    return {"status": "queued_for_review", "ticket_id": ticket_id, "reason": reason, "payload": payload or {}}


def list_account_ids() -> list[str]:
    """Demo account ids, for UIs that need to offer a picker (no real lookup service)."""
    return list(_ACCOUNTS.keys())
