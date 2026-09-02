"""Regression test: account_lookup must never emit a full SSN, PAN, or CVV.

The repo has no pytest dependency in ``uv.lock``, so this module is written to
run either under pytest or directly via ``python tests/test_account_lookup_redaction.py``.
"""

from __future__ import annotations

import json
import re

from concierge.mock_data import CUSTOMERS
from concierge.tools import account_lookup

NINE_DIGIT_SSN = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")


def test_account_lookup_redacts_sensitive_fields() -> None:
    for customer_id, customer in CUSTOMERS.items():
        result = account_lookup.invoke({"customer_id": customer_id})
        blob = json.dumps(result)

        assert "ssn" not in result
        assert "cvv" not in blob
        assert NINE_DIGIT_SSN.search(blob) is None
        assert customer["ssn"] not in blob
        assert result["ssn_last4"] == customer["ssn"].replace("-", "")[-4:]

        for card, redacted in zip(customer["credit_cards"], result["credit_cards"]):
            assert "number" not in redacted
            assert card["number"] not in blob
            assert redacted["number_masked"] == f"**** {card['number'][-4:]}"

        assert result["customer_id"] == customer["customer_id"]
        assert result["name"] == customer["name"]
        assert result["phone"] == customer["phone"]
        assert result["email"] == customer["email"]
        assert result["accounts"] == customer["accounts"]


if __name__ == "__main__":
    test_account_lookup_redacts_sensitive_fields()
    print("ok")
