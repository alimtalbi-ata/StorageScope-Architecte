"""V6.235: reject spoofed collector provenance, never auto-merge CMDB.

Synthetic, read-only tests. Author: Abdelhalim Talbi.
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


class CollectorProvenanceTests(unittest.TestCase):
    def test_fullwidth_source_cannot_masquerade_as_independent_collector(self):
        records = [{'source': 'CMDB', 'serial': 'S-100'},
                   {'source': 'ＣＭＤＢ', 'serial': 's-100'}]
        before = copy.deepcopy(records)
        report = reconcile(records)
        self.assertEqual(report['candidate_count'], 1)
        self.assertEqual(report['duplicate_source_indices'], [0, 1])
        self.assertEqual(report['candidates'][0]['action'], 'QUARANTINE_DUPLICATE_SOURCE_OBSERVATION')
        self.assertEqual(report['quarantined_indices'], [0, 1])
        self.assertEqual(report['automatic_merges'], 0)
        self.assertEqual(records, before)

    def test_invisible_format_character_is_invalid_and_taints_matching_identity(self):
        records = [{'source': 'cm\u200bdb', 'serial': 'A'},
                   {'source': 'cmdb', 'serial': 'a'},
                   {'source': 'probe', 'serial': 'A'},
                   {'source': 'cmdb', 'serial': 'SAFE'},
                   {'source': 'probe', 'serial': 'safe'}]
        report = reconcile(records)
        self.assertEqual(report['invalid_records'], [{'index': 0, 'reason': 'invalid_source'}])
        self.assertEqual(report['invalid_identity_link_indices'], [1, 2])
        self.assertEqual(report['quarantined_indices'], [1, 2])
        self.assertEqual([c['action'] for c in report['candidates']],
                         ['QUARANTINE_LINKED_INVALID_RECORD', 'REVIEW_REQUIRED'])

    def test_line_break_and_ansi_escape_source_are_rejected(self):
        for source in ('collector\nFAKE', 'collector\x1b[31m', 'collector\u202e'):
            with self.subTest(source=repr(source)):
                report = reconcile([{'source': source, 'wwn': 'WWN1'},
                                    {'source': 'cmdb', 'wwn': 'wwn1'}])
                self.assertEqual(report['invalid_records'][0]['reason'], 'invalid_source')
                self.assertEqual(report['invalid_identity_link_indices'], [1])
                self.assertEqual(report['candidate_count'], 0)

    def test_oversized_collector_identifier_is_not_trusted(self):
        report = reconcile([{'source': 'X' * 257, 'uuid': 'U1'},
                            {'source': 'cmdb', 'uuid': 'u1'}])
        self.assertEqual(report['invalid_records'][0]['reason'], 'invalid_source')
        self.assertEqual(report['invalid_identity_link_indices'], [1])

    def test_legitimate_unicode_collector_and_spaces_still_reconcile(self):
        report = reconcile([{'source': '  Équipe   SAN  ', 'serial': 'X'},
                            {'source': 'probe', 'serial': 'x'}])
        self.assertEqual(report['assessment'], 'REVIEW_REQUIRED')
        self.assertEqual(report['quarantined_indices'], [])
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')

    def test_fullwidth_placeholder_is_not_a_strong_identity(self):
        records = [{'source': 'cmdb', 'serial': 'Ｎ／Ａ'},
                   {'source': 'probe', 'serial': 'n/a'}]
        report = reconcile(records)
        self.assertEqual(report['candidate_count'], 0)
        self.assertEqual([entry['reason'] for entry in report['invalid_records']],
                         ['missing_strong_identity', 'missing_strong_identity'])
        self.assertEqual(report['automatic_merges'], 0)

    def test_control_character_in_one_strong_id_invalidates_whole_record(self):
        records = [{'source': 'legacy-export', 'serial': 'SER' + chr(10) + 'IAL', 'uuid': 'U-1'},
                   {'source': 'cmdb', 'uuid': 'u-1'},
                   {'source': 'probe', 'uuid': 'U-1'}]
        report = reconcile(records)
        self.assertEqual(report['invalid_records'],
                         [{'index': 0, 'reason': 'invalid_identity_value:serial'}])
        self.assertEqual(report['invalid_identity_link_indices'], [1, 2])
        self.assertEqual(report['quarantined_indices'], [1, 2])
        self.assertEqual(report['automatic_merges'], 0)

    def test_oversized_strong_identity_is_rejected_and_taints_linked_record(self):
        records = [{'source': 'legacy-export', 'serial': 'S' * 513, 'uuid': 'U-2'},
                   {'source': 'cmdb', 'uuid': 'u-2'}]
        report = reconcile(records)
        self.assertEqual(report['invalid_records'],
                         [{'index': 0, 'reason': 'invalid_identity_value:serial'}])
        self.assertEqual(report['invalid_identity_link_indices'], [1])
        self.assertEqual(report['quarantined_indices'], [1])

    def test_desktop_sha256_and_read_only_report_for_spoofed_source(self):
        records = [{'source': 'CMDB', 'serial': 'X'},
                   {'source': 'ＣＭＤＢ', 'serial': 'x'}]
        raw = json.dumps(records, ensure_ascii=False).encode('utf-8')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'inventory.json'
            path.write_bytes(raw)
            report = review_cmdb_file(path)
            self.assertEqual(report['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(path.read_bytes(), raw)
            self.assertIn('Doublons intra-source', format_cmdb_report(report))
            self.assertEqual(report['destructive_changes'], 0)


if __name__ == '__main__':
    unittest.main()
