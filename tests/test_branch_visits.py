"""Tests for the branch_visits tool."""

from __future__ import annotations

import unittest

from concierge.tools import branch_visits


class BranchVisitsTest(unittest.TestCase):
    def test_returns_visits_newest_first(self):
        result = branch_visits.invoke({"customer_id": "CUST-0005"})
        dates = [visit["date"] for visit in result["visits"]]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertEqual(result["visits"][0]["branch"], "Meridian National - Downtown Austin")
        self.assertIn("purpose", result["visits"][0])

    def test_respects_limit(self):
        result = branch_visits.invoke({"customer_id": "CUST-0004", "limit": 2})
        self.assertEqual(len(result["visits"]), 2)

    def test_customer_without_visits_gets_explanation(self):
        result = branch_visits.invoke({"customer_id": "CUST-0003"})
        self.assertEqual(result["visits"], [])
        self.assertIn("No in-person branch visits", result["message"])

    def test_unknown_customer_raises(self):
        with self.assertRaises(ValueError):
            branch_visits.invoke({"customer_id": "NOPE-1"})


if __name__ == "__main__":
    unittest.main()
