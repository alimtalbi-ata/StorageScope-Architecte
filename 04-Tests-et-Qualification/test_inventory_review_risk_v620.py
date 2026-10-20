"""Regression tests for non-destructive inventory identity review."""
import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "03-Sources"))
from inventory_review_risk_v620 import review_inventory
from governance_service import assess
from governance_desktop import explain_candidate

class InventoryRiskTests(unittest.TestCase):
    def test_conflicting_wwn_is_high_risk(self):
        rows = [
            {"source": "A", "serial": "SN1", "wwn": "500a", "name": "array"},
            {"source": "B", "serial": "sn1", "wwn": "500b", "name": "array"},
        ]
        original = [dict(x) for x in rows]
        report = review_inventory(rows)
        self.assertEqual(rows, original)
        self.assertEqual(report["high_risk_count"], 1)
        self.assertEqual(report["candidates"][0]["identity_disagreements"], ["wwn"])
        self.assertTrue(report["candidates"][0]["review_required"])
        self.assertEqual(report["automatic_merges"], 0)

    def test_same_source_duplicate_requires_review(self):
        rows = [{"source": "A", "uuid": "X"}, {"source": "A", "uuid": "x"}]
        candidate = review_inventory(rows)["candidates"][0]
        self.assertTrue(candidate["same_source"])
        self.assertEqual(candidate["risk"], "MEDIUM")

    def test_governance_exposes_risk_and_keeps_human_review(self):
        rows = [
            {"source": "A", "id": "a", "name": "one", "type": "array", "serial": "S1", "wwn": "500a"},
            {"source": "B", "id": "b", "name": "two", "type": "array", "serial": "S1", "wwn": "500b"},
        ]
        report = assess(rows)
        candidate = report["reconciliation"]["candidates"][0]
        self.assertEqual(candidate["risk"], "HIGH")
        self.assertEqual(candidate["identity_disagreements"], ["wwn"])
        self.assertEqual(explain_candidate(candidate)["risk"], "HIGH")
        self.assertEqual(report["automatic_merges"], 0)

    def test_clean_cross_source_candidate(self):
        rows = [{"source": "A", "serial": "X"}, {"source": "B", "serial": "x"}]
        candidate = review_inventory(rows)["candidates"][0]
        self.assertEqual(candidate["risk"], "LOW")
        self.assertTrue(candidate["review_required"])

if __name__ == "__main__":
    unittest.main()
