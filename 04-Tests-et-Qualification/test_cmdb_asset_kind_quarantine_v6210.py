"""V6.210 fail-closed CMDB asset-kind identity regression (synthetic data).

Author: Abdelhalim Talbi. Read-only; no real CMDB or vendor calls.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from inventory_reconcile_v619 import reconcile
from cmdb_review_desktop_v6198 import review_cmdb_file, format_cmdb_report


class CMDBAssetKindQuarantineTests(unittest.TestCase):
    def test_shared_serial_across_nas_and_host_is_quarantined(self):
        records = [{'source': 'CMDB', 'serial': 'S1', 'kind': 'nas'},
                   {'source': 'collector', 'serial': 's1', 'type': 'host'}]
        before = copy.deepcopy(records)
        result = reconcile(records)
        self.assertEqual(result['quarantined_indices'], [0, 1])
        self.assertEqual(result['candidates'][0]['action'], 'QUARANTINE_IDENTITY_CONFLICT')
        self.assertEqual(result['candidates'][0]['identity_conflicts'], [
            {'field': 'asset_kind', 'left': 'nas', 'right': 'host'}])
        self.assertEqual(result['automatic_merges'], 0)
        self.assertEqual(records, before)

    def test_conflict_propagates_to_untyped_neighbor_only(self):
        records = [{'source': 'CMDB', 'serial': 'S1', 'kind': 'nas'},
                   {'source': 'collector', 'serial': 'S1', 'kind': 'host'},
                   {'source': 'other', 'serial': 'S1'},
                   {'source': 'CMDB', 'serial': 'S2', 'kind': 'nas'},
                   {'source': 'collector', 'serial': 'S2', 'kind': 'nas'}]
        report = reconcile(records)
        self.assertEqual(report['direct_conflict_indices'], [0, 1])
        self.assertEqual(report['propagated_quarantine_indices'], [2])
        self.assertEqual(report['quarantined_indices'], [0, 1, 2])
        actions = {tuple(c['indices']): c['action'] for c in report['candidates']}
        self.assertEqual(actions[(0, 2)], 'QUARANTINE_LINKED_IDENTITY_CONFLICT')
        self.assertEqual(actions[(3, 4)], 'REVIEW_REQUIRED')
        self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_aliases_do_not_create_false_kind_conflicts(self):
        report = reconcile([{'source': 'a', 'serial': 'S1', 'kind': 'array'},
                            {'source': 'b', 'serial': 'S1', 'type': 'storage_array'}])
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')
        self.assertEqual(report['quarantined_indices'], [])

    def test_missing_kind_preserves_review_only_behavior(self):
        report = reconcile([{'source': 'a', 'uuid': 'U1'},
                            {'source': 'b', 'uuid': 'u1', 'kind': 'nas'}])
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')
        self.assertEqual(report['automatic_merges'], 0)

    def test_self_contradictory_kind_is_excluded_from_matching(self):
        report = reconcile([{'source': 'a', 'serial': 'S1', 'kind': 'nas', 'type': 'host'},
                            {'source': 'b', 'serial': 'S1', 'kind': 'nas'}])
        self.assertEqual(report['invalid_records'], [{'index': 0, 'reason': 'conflicting_asset_kind'}])
        self.assertEqual(report['candidate_count'], 0)
        self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_invalid_kind_is_not_trusted(self):
        for invalid in (True, '', [], 42):
            with self.subTest(invalid=invalid):
                report = reconcile([{'source': 'a', 'serial': 'S1', 'kind': invalid},
                                    {'source': 'b', 'serial': 'S1', 'kind': 'nas'}])
                self.assertEqual(report['invalid_records'], [{'index': 0, 'reason': 'invalid_asset_kind'}])
                self.assertEqual(report['candidate_count'], 0)

    def test_permutations_preserve_quarantine(self):
        records = [{'source': 'a', 'serial': 'S1', 'kind': 'nas'},
                   {'source': 'b', 'serial': 'S1', 'kind': 'host'},
                   {'source': 'c', 'serial': 'S1'}]
        for variant in (records, list(reversed(records)), records[1:] + records[:1]):
            with self.subTest(variant=variant):
                report = reconcile(variant)
                self.assertEqual(len(report['quarantined_indices']), 3)
                self.assertEqual(len(report['propagated_quarantine_indices']), 1)

    def test_desktop_report_preserves_snapshot_and_displays_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.json'
            raw = json.dumps([{'source': 'CMDB', 'serial': 'S1', 'kind': 'nas'},
                              {'source': 'collector', 'serial': 'S1', 'type': 'host'}]).encode('utf-8')
            path.write_bytes(raw)
            report = review_cmdb_file(path)
            self.assertIn('asset_kind', format_cmdb_report(report))
            self.assertEqual(report['assessment'], 'INCOMPLETE')
            self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
