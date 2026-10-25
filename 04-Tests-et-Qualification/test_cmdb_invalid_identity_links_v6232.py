"""V6.232 CMDB invalid identity quarantine; synthetic read-only fixtures.
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


class InvalidIdentityLinkTests(unittest.TestCase):
    def test_invalid_secondary_identifier_quarantines_valid_pair(self):
        data = [{'source': 'broken', 'serial': 'S1', 'wwn': 123},
                {'source': 'cmdb', 'serial': 's1', 'wwn': 'WWN-A'},
                {'source': 'array', 'serial': 'S1', 'wwn': 'wwn-a'}]
        report = reconcile(data)
        self.assertEqual(report['invalid_records'], [{'index': 0, 'reason': 'invalid_identity_type:wwn'}])
        self.assertEqual(report['candidate_count'], 1)
        self.assertEqual(report['candidates'][0]['action'], 'QUARANTINE_LINKED_INVALID_RECORD')
        self.assertEqual(report['invalid_identity_origin_indices'], [0])
        self.assertEqual(report['invalid_identity_link_indices'], [1, 2])
        self.assertEqual(report['quarantined_indices'], [1, 2])

    def test_transitive_quarantine_and_unrelated_review(self):
        data = [{'source': 'bad', 'serial': 'S1', 'vendor': 100},
                {'source': 'cmdb', 'serial': 's1', 'uuid': 'U2'},
                {'source': 'probe', 'uuid': 'u2'},
                {'source': 'cmdb', 'serial': 'SAFE'},
                {'source': 'probe', 'serial': 'safe'}]
        report = reconcile(data)
        self.assertEqual(report['candidate_count'], 2)
        self.assertEqual(report['invalid_identity_link_indices'], [1])
        self.assertEqual(report['propagated_quarantine_indices'], [2])
        self.assertEqual(report['quarantined_indices'], [1, 2])
        self.assertEqual([c['action'] for c in report['candidates']],
                         ['QUARANTINE_LINKED_INVALID_RECORD', 'REVIEW_REQUIRED'])

    def test_missing_provenance_taints_without_candidate(self):
        report = reconcile([{'serial': 'X'}, {'source': 'cmdb', 'serial': 'x'},
                            {'source': 'array', 'serial': 'X'}])
        self.assertEqual(report['candidate_count'], 1)
        self.assertEqual(report['invalid_records'][0]['reason'], 'missing_source')
        self.assertEqual(report['candidates'][0]['action'], 'QUARANTINE_LINKED_INVALID_RECORD')

    def test_unknown_nonobject_and_cross_field_do_not_taint(self):
        report = reconcile([{'source': 'bad', 'serial': 'N/A', 'wwn': 3}, None,
                            {'source': 'cmdb', 'serial': 'OK'},
                            {'source': 'array', 'serial': 'ok'}])
        self.assertEqual(report['invalid_identity_link_indices'], [])
        self.assertEqual(report['quarantined_indices'], [])
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')
        report = reconcile([{'source': 'bad', 'serial': 'ABC', 'wwn': []},
                            {'source': 'cmdb', 'wwn': 'abc'},
                            {'source': 'array', 'wwn': 'ABC'}])
        self.assertEqual(report['invalid_identity_link_indices'], [])
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')

    def test_direct_conflict_priority(self):
        report = reconcile([{'source': 'bad', 'serial': 'X', 'wwn': 3},
                            {'source': 'cmdb', 'serial': 'X', 'uuid': 'U1'},
                            {'source': 'array', 'serial': 'x', 'uuid': 'U2'}])
        self.assertEqual(report['candidates'][0]['action'], 'QUARANTINE_IDENTITY_CONFLICT')
        self.assertEqual(report['quarantined_indices'], [1, 2])

    def test_snapshot_read_only_and_ui_reason(self):
        data = [{'source': 'bad', 'serial': 'S1', 'uuid': {}},
                {'source': 'cmdb', 'serial': 'S1'},
                {'source': 'array', 'serial': 's1'}]
        before = copy.deepcopy(data)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'snapshot.json'
            raw = json.dumps(data).encode('utf-8')
            source.write_bytes(raw)
            report = review_cmdb_file(source)
            self.assertEqual(report['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertIn('QUARANTINE_LINKED_INVALID_RECORD', format_cmdb_report(report))
            self.assertIn('Identités liées à des observations invalides', format_cmdb_report(report))
            self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(data, before)
        self.assertEqual(report['automatic_merges'], 0)
        self.assertEqual(report['destructive_changes'], 0)


if __name__ == '__main__':
    unittest.main()
