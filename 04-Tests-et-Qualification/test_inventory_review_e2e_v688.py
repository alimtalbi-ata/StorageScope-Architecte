"""StorageScope end-to-end review across NetApp, Pure and Dell PowerScale."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "03-Sources"))
from governance_service import assess
from governance_desktop import eligible_candidates, can_decide, history_for_selection
from review_registry_v622 import decide, verify

class MultiVendorReviewE2E(unittest.TestCase):
    def test_complete_review_and_blocked_identity(self):
        records = [
            {"source":"netapp", "asset_id":"NETAPP-01", "serial":"SERIAL-100", "model":"AFF"},
            {"source":"pure-flashblade", "asset_id":"PURE-01", "serial":"SERIAL-100", "model":"FlashBlade"},
            {"source":"dell-powerscale", "asset_id":"ISILON-01", "serial":"SERIAL-200", "wwn":"WWN-1"},
            {"source":"netapp", "asset_id":"NETAPP-02", "serial":"SERIAL-200", "wwn":"WWN-2"},
        ]
        original = json.dumps(records, sort_keys=True)
        report = assess(records)
        self.assertEqual(json.dumps(records, sort_keys=True), original)
        rows = eligible_candidates(report)
        self.assertGreaterEqual(len(rows), 2)
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "review.sqlite"
            eligible = [(key, candidate) for key, candidate in rows if can_decide(candidate)]
            blocked = [(key, candidate) for key, candidate in rows if not can_decide(candidate)]
            self.assertTrue(eligible, "At least one candidate should be human-reviewable")
            self.assertTrue(blocked, "Contradictory identities must remain visible but blocked")
            self.assertFalse(db.exists())
            for key, candidate in blocked:
                self.assertFalse(can_decide(candidate))
            self.assertFalse(db.exists(), "Read-only assessment must not create SQLite")
            key, _ = eligible[0]
            result = decide(db, report, key, "APPROVED", "human-reviewer", "cross-source check")
            self.assertFalse(result["inventory_changed"])
            self.assertTrue(verify(db)["valid"])
            history = history_for_selection(db, key)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["candidate_key"], key)
            with self.assertRaises(ValueError):
                decide(db, report, key, "REJECTED", "human-reviewer", "overwrite")
            self.assertEqual(len(history_for_selection(db)), 1)
            self.assertTrue(verify(db)["valid"])
            self.assertEqual(json.dumps(records, sort_keys=True), original)

if __name__ == "__main__":
    unittest.main()
