"""V6.233: transitive duplicate collector provenance; synthetic, read-only.
Author: Abdelhalim Talbi.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '03-Sources'))
from inventory_reconcile_v619 import reconcile
from cmdb_review_desktop_v6198 import review_cmdb_file, format_cmdb_report


class TransitiveDuplicateSourceTests(unittest.TestCase):
    def test_same_source_connected_through_different_identifiers_is_quarantined(self):
        records = [
            {'source': ' CMDB ', 'serial': 'S1'},
            {'source': 'probe', 'serial': 's1', 'uuid': 'U2'},
            {'source': 'cmdb', 'uuid': 'u2'},
        ]
        before = copy.deepcopy(records)
        report = reconcile(records)
        self.assertEqual(report['candidate_count'], 2)
        self.assertEqual(report['duplicate_source_indices'], [0, 2])
        self.assertEqual(report['transitive_duplicate_source_indices'], [0, 2])
        self.assertEqual(report['quarantined_indices'], [0, 1, 2])
        self.assertEqual([c['action'] for c in report['candidates']],
                         ['QUARANTINE_LINKED_DUPLICATE_SOURCE_OBSERVATION'] * 2)
        self.assertEqual(report['assessment'], 'INCOMPLETE')
        self.assertEqual(records, before)

    def test_unrelated_component_remains_reviewable(self):
        report = reconcile([
            {'source': 'cmdb', 'serial': 'S1'},
            {'source': 'probe', 'serial': 'S1', 'uuid': 'U2'},
            {'source': 'CMDB', 'uuid': 'U2'},
            {'source': 'cmdb', 'serial': 'SAFE'},
            {'source': 'probe', 'serial': 'safe'},
        ])
        self.assertEqual(report['quarantined_indices'], [0, 1, 2])
        self.assertEqual(report['candidates'][-1]['action'], 'REVIEW_REQUIRED')

    def test_three_independent_sources_remain_reviewable(self):
        report = reconcile([
            {'source': 'cmdb', 'serial': 'S1'},
            {'source': 'probe', 'serial': 's1', 'uuid': 'U2'},
            {'source': 'array', 'uuid': 'u2'},
        ])
        self.assertEqual(report['duplicate_source_indices'], [])
        self.assertEqual(report['transitive_duplicate_source_indices'], [])
        self.assertEqual(report['quarantined_indices'], [])
        self.assertTrue(all(c['action'] == 'REVIEW_REQUIRED' for c in report['candidates']))

    def test_direct_identity_conflict_keeps_priority(self):
        report = reconcile([
            {'source': 'cmdb', 'serial': 'S1', 'wwn': 'A'},
            {'source': 'probe', 'serial': 'S1', 'uuid': 'U2', 'wwn': 'B'},
            {'source': 'CMDB', 'uuid': 'U2'},
        ])
        self.assertEqual(report['candidates'][0]['action'], 'QUARANTINE_IDENTITY_CONFLICT')
        self.assertEqual(report['quarantined_indices'], [0, 1, 2])
        self.assertEqual(report['transitive_duplicate_source_indices'], [0, 2])

    def test_desktop_snapshot_sha256_and_human_explanation(self):
        records = [{'source': 'cmdb', 'serial': 'S1'},
                   {'source': 'probe', 'serial': 'S1', 'uuid': 'U2'},
                   {'source': 'CMDB', 'uuid': 'U2'}]
        raw = json.dumps(records).encode('utf-8')
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'inventory.json'
            source.write_bytes(raw)
            report = review_cmdb_file(source)
            self.assertEqual(report['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(source.read_bytes(), raw)
            self.assertIn('Doublons intra-source transitifs', format_cmdb_report(report))
            self.assertIn('QUARANTINE_LINKED_DUPLICATE_SOURCE_OBSERVATION', format_cmdb_report(report))
            self.assertEqual(report['automatic_merges'], 0)
            self.assertEqual(report['destructive_changes'], 0)


if __name__ == '__main__':
    unittest.main()
