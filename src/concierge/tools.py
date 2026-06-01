"""Tools available to the Meridian National customer service concierge agent.

A few tools have deliberate rough edges so LangSmith Engine has something
to cluster after the load generator runs:

- search_banking_docs has a vague description so the model occasionally
  re-queries multiple times rephrasing
- account_lookup raises on malformed customer IDs and on IDs prefixed with
  "X" (simulated downstream outage)
- recent_transactions raises if the model passes a runaway limit
- find_branch raises on non-zip inputs
"""

from __future__ import annotations

import re

from langchain_core.tools import tool

from concierge.mock_data import (
    BRANCHES,
    CUSTOMERS,
    TRANSACTIONS,
    find_branch_by_zip,
)
from concierge.retrieval import retrieve


@tool
def search_banking_docs(query: str, k: int = 4) -> str:
    """Search Meridian National banking documentation.

    Args:
        query: A natural-language search query.
        k: Number of relevant chunks to return. Defaults to 4.
    """
    chunks = retrieve(query, k=k)
    if not chunks:
        return "No relevant documentation found."
    blocks = []
    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        blocks.append(f"[source: {source}]\n{chunk.page_content}")
    return "\n\n---\n\n".join(blocks)


@tool
def account_lookup(customer_id: str) -> dict:
    """Look up account information by Meridian customer ID. customer_id MUST match CUST-####; if the rep only has an SSN/phone/email/card, call find_customer_by_identifier first to resolve the ID, then call this. Never pass an SSN, phone, or card number here."""
    if not re.fullmatch(r"CUST-\d{4}", customer_id):
        raise ValueError(
            f"customer_id must be in the format CUST-#### (e.g. CUST-0001). "
            f"Got {customer_id!r}. If you only have an SSN, phone, email, or "
            "card on file, call find_customer_by_identifier first to resolve "
            "the CUST-#### id, then call account_lookup. Do not guess or "
            "enumerate customer IDs."
        )
    if customer_id.startswith("X"):
        raise RuntimeError(
            "Customer record service is temporarily unavailable. Try again later."
        )
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        raise ValueError(
            f"No customer found with ID {customer_id!r}. "
            "Customer IDs are in the format CUST-####."
        )
    return dict(customer)


@tool
def find_customer_by_identifier(identifier_type: str, value: str) -> dict:
    """Resolve a CUST-#### customer ID from an SSN, phone, email, or card last-4. identifier_type must be one of 'ssn', 'phone', 'email', 'card_last4'."""
    allowed = {"ssn", "phone", "email", "card_last4"}
    if identifier_type not in allowed:
        raise ValueError(
            f"identifier_type must be one of {sorted(allowed)}. "
            f"Got {identifier_type!r}."
        )
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be a non-empty string.")

    needle = value.strip()
    if identifier_type == "phone":
        needle_norm = re.sub(r"\D", "", needle)
    elif identifier_type == "email":
        needle_norm = needle.lower()
    else:
        needle_norm = needle

    matches: list[str] = []
    for cust_id, customer in CUSTOMERS.items():
        if identifier_type == "ssn":
            if customer["ssn"] == needle_norm:
                matches.append(cust_id)
        elif identifier_type == "phone":
            if re.sub(r"\D", "", customer["phone"]) == needle_norm:
                matches.append(cust_id)
        elif identifier_type == "email":
            if customer["email"].lower() == needle_norm:
                matches.append(cust_id)
        elif identifier_type == "card_last4":
            for card in customer.get("credit_cards", []):
                digits = re.sub(r"\D", "", card.get("number", ""))
                if digits.endswith(needle_norm):
                    matches.append(cust_id)
                    break

    if len(matches) == 1:
        return {"customer_id": matches[0]}
    return {"customer_id": None, "match_count": len(matches)}


@tool
def recent_transactions(customer_id: str, limit: int = 5) -> list[dict]:
    """Retrieve a customer's most recent transactions.

    Args:
        customer_id: The customer ID (e.g. CUST-0001).
        limit: Optional number of transactions to return.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if limit > 50:
        raise ValueError(
            f"limit {limit} exceeds the maximum of 50. Pick a smaller number."
        )
    if customer_id not in CUSTOMERS:
        raise ValueError(
            f"No customer found with ID {customer_id!r}. "
            "Customer IDs are in the format CUST-####."
        )
    txs = TRANSACTIONS.get(customer_id, [])
    return [dict(t) for t in txs[:limit]]


@tool
def find_branch(zip_code: str) -> dict:
    """Find a Meridian National branch.

    Args:
        zip_code: A 5-digit U.S. ZIP code.
    """
    if not (isinstance(zip_code, str) and len(zip_code) == 5 and zip_code.isdigit()):
        raise ValueError(
            f"zip_code must be a 5-digit U.S. ZIP code. Got {zip_code!r}."
        )
    branch = find_branch_by_zip(zip_code)
    if branch is None:
        return {
            "match": False,
            "message": "No Meridian National branch found in our directory for that ZIP code.",
            "nearest_known": BRANCHES[0],
        }
    return {"match": True, **branch}


@tool
def transfer_funds(from_account: str, to_account: str, amount: float) -> dict:
    """Initiate a transfer between two Meridian National accounts owned by the same customer.

    Args:
        from_account: The source account ID.
        to_account: The destination account ID.
        amount: The dollar amount to transfer.
    """
    if amount <= 0:
        raise ValueError("amount must be positive")
    confirmation = f"MNB-XFER-{abs(hash((from_account, to_account, amount))) % 10_000_000:07d}"
    return {
        "status": "submitted",
        "from_account": from_account,
        "to_account": to_account,
        "amount": round(amount, 2),
        "confirmation": confirmation,
        "estimated_post": "immediately",
    }


TOOLS = [
    search_banking_docs,
    account_lookup,
    find_customer_by_identifier,
    recent_transactions,
    find_branch,
    transfer_funds,
]
