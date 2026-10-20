"""Regression of StorageScope P0 human review decision gate. Author: Abdelhalim Talbi."""
import copy
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from governance_service import assess
from governance_desktop import eligible_candidates, can_decide
from review_registry_v622 import candidate_key, decide, verify


class DecisionGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'review.sqlite'

    def test_eligible_service_candidate_can_be_reviewed_end_to_end(self):
        records = [
            {'id': 'host-a', 'name': 'A', 'type': 'storage', 'source': 'netapp', 'serial': '123', 'vendor': 'NetApp'},
            {'id': 'host-b', 'name': 'B', 'type': 'storage', 'source': 'discovery', 'serial': '123', 'vendor': 'NetApp'},
        ]
        baseline = copy.deepcopy(records)
        report = assess(records)
        rows = eligible_candidates(report)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1]['review_eligibility'], 'ELIGIBLE')
        self.assertTrue(can_decide(rows[0][1]))
        result = decide(self.db, report, rows[0][0], 'REJECTED', 'architect', 'validated against array inventory')
        self.assertFalse(result['inventory_changed'])
        self.assertTrue(verify(self.db)['valid'])
        self.assertEqual(records, baseline)

    def test_blocked_contradiction_rejected_before_database_creation(self):
        records = [
            {'id': 'ci-a', 'name': 'A', 'type': 'storage', 'source': 'scan', 'serial': '123', 'wwn': '500a', 'vendor': 'Dell'},
            {'id': 'ci-b', 'name': 'B', 'type': 'storage', 'source': 'cmdb', 'serial': '123', 'wwn': '500b', 'vendor': 'Dell'},
        ]
        report = assess(records)
        candidate = report['reconciliation']['candidates'][0]
        self.assertEqual(candidate['review_eligibility'], 'BLOCKED_CONTRADICTION')
        with self.assertRaises(ValueError):
            decide(self.db, report, candidate_key(candidate), 'APPROVED', 'architect', 'not permitted')
        self.assertFalse(self.db.exists())

    def test_mixed_invalid_candidate_does_not_block_valid_one(self):
        valid = {'asset_ids': ['a', 'b'], 'identity_evidence': ['serial'], 'review_eligibility': 'ELIGIBLE'}
        blocked = {'asset_ids': [None, None], 'review_eligibility': 'MISSING_OR_AMBIGUOUS_STABLE_ID'}
        report = {'reconciliation': {'candidates': [blocked, valid]}}
        decide(self.db, report, candidate_key(valid), 'REJECTED', 'architect', 'different arrays')
        self.assertTrue(verify(self.db)['valid'])

    def test_duplicate_candidate_keys_fail_closed(self):
        candidate = {'asset_ids': ['a', 'b'], 'identity_evidence': ['serial'], 'review_eligibility': 'ELIGIBLE'}
        report = {'reconciliation': {'candidates': [candidate, copy.deepcopy(candidate)]}}
        with self.assertRaises(ValueError):
            decide(self.db, report, candidate_key(candidate), 'APPROVED', 'architect', 'duplicate')
        self.assertFalse(self.db.exists())

    def test_stale_or_forged_review_key_rejected(self):
        candidate = {'asset_ids': ['a', 'b'], 'identity_evidence': ['serial'],
                     'review_eligibility': 'ELIGIBLE', 'review_key': 'stale-key'}
        with self.assertRaises(ValueError):
            decide(self.db, {'reconciliation': {'candidates': [candidate]}},
                   candidate_key(candidate), 'APPROVED', 'architect', 'stale')
        self.assertFalse(self.db.exists())

    def test_blocked_candidate_does_not_mask_valid_one(self):
        valid = {'asset_ids': ['c', 'd'], 'identity_evidence': ['serial'], 'review_eligibility': 'ELIGIBLE'}
        blocked = {'asset_ids': ['a', 'b'], 'identity_evidence': ['serial'],
                   'review_eligibility': 'BLOCKED_CONTRADICTION', 'action': 'BLOCKED'}
        report = {'reconciliation': {'candidates': [blocked, valid]}}
        decide(self.db, report, candidate_key(valid), 'REJECTED', 'architect', 'reviewed')
        self.assertTrue(verify(self.db)['valid'])

    def test_high_risk_is_rejected(self):
        candidate = {'asset_ids': ['a', 'b'], 'identity_evidence': ['serial'],
                     'review_eligibility': 'ELIGIBLE', 'risk': 'HIGH'}
        with self.assertRaises(ValueError):
            decide(self.db, {'reconciliation': {'candidates': [candidate]}},
                   candidate_key(candidate), 'APPROVED', 'architect', 'unsafe')
        self.assertFalse(self.db.exists())

    def test_ui_rejects_stale_review_key(self):
        candidate = {'asset_ids': ['a', 'b'], 'identity_evidence': ['serial'],
                     'review_eligibility': 'ELIGIBLE', 'review_key': 'old'}
        self.assertFalse(can_decide(candidate))


if __name__ == '__main__':
    unittest.main()
