"""V6.231: malformed strong CMDB identity types must never become match evidence.
All fixtures synthetic; no CMDB writes. Author: Abdelhalim Talbi.
"""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '03-Sources'))
from inventory_reconcile_v619 import reconcile
from cmdb_review_desktop_v6198 import review_cmdb_file, format_cmdb_report


class StrongIdentityTypeTests(unittest.TestCase):
    def test_invalid_secondary_wwn_blocks_otherwise_matching_serial(self):
        result = reconcile([{'source': 'CMDB', 'serial': 'S1', 'wwn': 5001},
                            {'source': 'collector', 'serial': 's1', 'wwn': '5001'}])
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual(result['candidate_count'], 0)
        self.assertEqual(result['invalid_records'], [{'index': 0, 'reason': 'invalid_identity_type:wwn'}])

    def test_all_strong_fields_reject_non_string_values(self):
        for field in ('serial', 'wwn', 'uuid'):
            for bad in (0, 123, False, [], {}, ['S1']):
                with self.subTest(field=field, bad=bad):
                    report = reconcile([{'source': 'a', 'serial': 'S1', field: bad},
                                        {'source': 'b', 'serial': 'S1'}])
                    self.assertEqual(report['assessment'], 'INCOMPLETE')
                    self.assertEqual(report['invalid_records'][0]['reason'], f'invalid_identity_type:{field}')
                    self.assertEqual(report['candidate_count'], 0)

    def test_missing_null_and_placeholder_ids_are_still_unknown(self):
        report = reconcile([{'source': 'a', 'serial': 'S1', 'wwn': None, 'uuid': 'N/A'},
                            {'source': 'b', 'serial': 's1', 'wwn': '', 'uuid': 'unknown'}])
        self.assertEqual(report['assessment'], 'REVIEW_REQUIRED')
        self.assertEqual(report['candidate_count'], 1)
        self.assertEqual(report['quarantined_indices'], [])

    def test_unrelated_valid_identity_still_reviewable(self):
        report = reconcile([{'source': 'bad', 'serial': 'S1', 'uuid': {'id': 'u1'}},
                            {'source': 'a', 'serial': 'S2'},
                            {'source': 'b', 'serial': 's2'}])
        self.assertEqual(report['assessment'], 'INCOMPLETE')
        self.assertEqual(report['candidate_count'], 1)
        self.assertEqual(report['candidates'][0]['indices'], [1, 2])
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')

    def test_snapshot_digest_and_desktop_report_preserved(self):
        raw = b'[ {"source":"a", "serial":"S1", "wwn":42}, {"source":"b", "serial":"S1"} ]\n'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'cmdb.json'
            source.write_bytes(raw)
            report = review_cmdb_file(source)
            self.assertEqual(report['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report['candidate_count'], 0)
            self.assertIn('invalid_identity_type:wwn', format_cmdb_report(report))
            self.assertEqual(source.read_bytes(), raw)

    def test_reconcile_does_not_mutate_untrusted_input(self):
        records = [{'source': 'a', 'serial': 'S1', 'uuid': [1]},
                   {'source': 'b', 'serial': 'S1'}]
        before = copy.deepcopy(records)
        report = reconcile(records)
        self.assertEqual(records, before)
        self.assertEqual(report['automatic_merges'], 0)
        self.assertEqual(report['destructive_changes'], 0)


if __name__ == '__main__':
    unittest.main()
