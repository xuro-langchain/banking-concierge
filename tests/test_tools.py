"""Tests for the concierge tool registry.

Written with plain asserts so they run under pytest or directly with
``python tests/test_tools.py`` — pytest is not a locked dependency of this repo.
"""

from __future__ import annotations

from concierge.tools import TOOLS, start_account_application


def test_start_account_application_records_savings_application():
    result = start_account_application.invoke(
        {
            "customer_id": "CUST-0005",
            "account_type": "Way2Save Savings",
            "applicant_name": "Maya Patel",
        }
    )
    assert result["status"] == "application_started"
    assert result["account_type"] == "Way2Save Savings"
    assert result["application_id"].startswith("MNB-APP-")
    assert result["minimum_opening_deposit"] == 25.00
    assert result["next_steps"]


def test_start_account_application_rejects_unknown_account_type():
    try:
        start_account_application.invoke(
            {
                "customer_id": None,
                "account_type": "Crypto Vault",
                "applicant_name": "Dana Cruz",
            }
        )
    except ValueError as exc:
        assert "Way2Save Savings" in str(exc)
    else:
        raise AssertionError("expected a ValueError for an unknown account_type")


def test_start_account_application_is_registered():
    assert start_account_application in TOOLS


if __name__ == "__main__":
    for name, case in sorted(globals().items()):
        if name.startswith("test_"):
            case()
            print(f"ok {name}")
