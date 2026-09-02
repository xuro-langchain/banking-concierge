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


CUSTOMER_ID_PATTERN = re.compile(r"^CUST-\d{4}$")


def _digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


@tool
def resolve_customer(identifier: str) -> dict:
    """Resolve a caller identifier (SSN, card number, phone, or email) to a customer ID.

    Args:
        identifier: An SSN, credit card number, phone number, or email address
            given by the representative.

    Returns {"match": True, "customer_id": "CUST-####"} only when the
    identifier matches exactly one customer on file, otherwise
    {"match": False}. No other customer fields are ever returned.
    """
    needle = identifier.strip().lower()
    needle_digits = _digits(needle)
    matches: set[str] = set()
    for customer_id, customer in CUSTOMERS.items():
        if needle and needle == customer["email"].strip().lower():
            matches.add(customer_id)
            continue
        if not needle_digits:
            continue
        on_file = [customer["ssn"], customer["phone"]]
        on_file += [card["number"] for card in customer["credit_cards"]]
        if any(needle_digits == _digits(value) for value in on_file):
            matches.add(customer_id)
    if len(matches) != 1:
        return {
            "match": False,
            "message": (
                "That identifier does not resolve to exactly one customer on "
                "file. Ask the representative for the caller's CUST-#### "
                "customer ID."
            ),
        }
    return {"match": True, "customer_id": matches.pop()}


@tool
def account_lookup(customer_id: str) -> dict:
    """Look up account information for a known customer ID.

    Args:
        customer_id: A literal CUST-#### identifier the representative
            supplied, or one returned by resolve_customer. Never construct
            this value from an SSN, card number, phone number, or email, and
            never guess or enumerate IDs (CUST-0001, CUST-0002, ...) to find a
            matching name — use resolve_customer for a caller identifier, and
            ask the representative for the ID when it cannot be resolved.

    Returns the customer's name and a list of their account IDs, account
    types, and balances.
    """
    if customer_id.startswith("X"):
        raise RuntimeError(
            "Customer record service is temporarily unavailable. Try again later."
        )
    if not CUSTOMER_ID_PATTERN.match(customer_id):
        raise ValueError(
            f"{customer_id!r} is not a customer ID. customer_id must be a "
            "literal CUST-#### identifier provided by the representative or "
            "returned by resolve_customer. It must never be derived from an "
            "SSN, card number, phone number, or email, and must never be "
            "guessed or enumerated. Call resolve_customer with the caller's "
            "identifier, or ask the representative for the CUST-#### ID."
        )
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        raise ValueError(
            f"No customer found with ID {customer_id!r}. Do not try other IDs "
            "to find a matching name — ask the representative for the "
            "caller's CUST-#### customer ID."
        )
    return dict(customer)


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
    resolve_customer,
    account_lookup,
    recent_transactions,
    find_branch,
    transfer_funds,
]
