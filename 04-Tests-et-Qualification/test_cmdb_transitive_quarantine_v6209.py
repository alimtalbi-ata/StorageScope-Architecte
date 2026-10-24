"""V6.209 synthetic CMDB identity-graph quarantine regression tests.

Author: Abdelhalim Talbi. No real vendor inventory or CMDB writes.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from inventory_reconcile_v619 import reconcile
from cmdb_review_desktop_v6198 import format_cmdb_report, review_cmdb_file


def fixture():
    return [
        {'source': 'NetApp', 'serial': 'S1', 'wwn': 'W1'},
        {'source': 'CMDB', 'serial': 's1', 'wwn': 'W2'},
        {'source': 'Dell', 'wwn': 'w1'},
        {'source': 'Pure', 'wwn': 'W1'},
        {'source': 'CMDB', 'serial': 'S9', 'wwn': 'W9'},
        {'source': 'NetApp', 'serial': 's9', 'wwn': 'w9'},
    ]


class TransitiveQuarantineTests(unittest.TestCase):
    def test_connected_identity_conflict_quarantines_all_neighbors(self):
        records = fixture()
        before = copy.deepcopy(records)
        report = reconcile(records)
        self.assertEqual(report['quarantined_indices'], [0, 1, 2, 3])
        self.assertEqual(report['direct_conflict_indices'], [0, 1])
        self.assertEqual(report['propagated_quarantine_indices'], [2, 3])
        actions = {tuple(c['indices']): c['action'] for c in report['candidates']}
        self.assertEqual(actions[(0, 1)], 'QUARANTINE_IDENTITY_CONFLICT')
        self.assertEqual(actions[(0, 2)], 'QUARANTINE_LINKED_IDENTITY_CONFLICT')
        self.assertEqual(actions[(2, 3)], 'QUARANTINE_LINKED_IDENTITY_CONFLICT')
        self.assertEqual(actions[(4, 5)], 'REVIEW_REQUIRED')
        self.assertEqual(report['assessment'], 'INCOMPLETE')
        self.assertEqual(report['automatic_merges'], 0)
        self.assertEqual(records, before)

    def test_permutation_does_not_change_quarantined_sources(self):
        records = fixture()
        for variant in (records, list(reversed(records)), records[2:] + records[:2]):
            report = reconcile(variant)
            quarantined = {variant[i].get('wwn') for i in report['quarantined_indices']}
            self.assertEqual(quarantined, {'W1', 'W2', 'w1'})
            self.assertEqual(len(report['propagated_quarantine_indices']), 2)
            self.assertEqual(report['assessment'], 'INCOMPLETE')
            self.assertEqual(sum(c['action'] == 'REVIEW_REQUIRED' for c in report['candidates']), 1)

    def test_healthy_component_stays_reviewable(self):
        report = reconcile(fixture()[4:])
        self.assertEqual(report['quarantined_indices'], [])
        self.assertEqual(report['direct_conflict_indices'], [])
        self.assertEqual(report['propagated_quarantine_indices'], [])
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')

    def test_desktop_report_shows_propagated_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.json'
            raw = json.dumps(fixture()).encode('utf-8')
            path.write_bytes(raw)
            report = review_cmdb_file(path)
            text = format_cmdb_report(report)
            self.assertIn('Quarantaine par propagation : 2', text)
            self.assertIn('QUARANTINE_LINKED_IDENTITY_CONFLICT', text)
            self.assertEqual(path.read_bytes(), raw)

    def test_multi_hop_identity_chain_is_fail_closed(self):
        records = [
            {'source': 'A', 'serial': 'S1', 'wwn': 'W1'},
            {'source': 'B', 'serial': 'S1', 'wwn': 'W2'},
            {'source': 'C', 'wwn': 'W1', 'uuid': 'U1'},
            {'source': 'D', 'uuid': 'U1'},
        ]
        report = reconcile(records)
        self.assertEqual(report['quarantined_indices'], [0, 1, 2, 3])
        self.assertEqual(report['propagated_quarantine_indices'], [2, 3])
        self.assertNotIn('REVIEW_REQUIRED', [c['action'] for c in report['candidates']])


if __name__ == '__main__':
    unittest.main()
