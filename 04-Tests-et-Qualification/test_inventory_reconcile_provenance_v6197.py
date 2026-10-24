"""V6.197 CMDB reconciliation provenance, contradiction and boundedness tests."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / '03-Sources' / 'inventory_reconcile_v619.py'
spec = importlib.util.spec_from_file_location('inventory_reconcile_v619', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ProvenanceTests(unittest.TestCase):
    def test_strong_match_with_sources_requires_review(self):
        report = mod.reconcile([{'source': 'NetApp', 'serial': 'ABC'},
                                {'source': 'CMDB', 'serial': 'abc'}])
        self.assertEqual(report['candidate_count'], 1)
        self.assertEqual(report['assessment'], 'REVIEW_REQUIRED')
        self.assertEqual(report['candidates'][0]['action'], 'REVIEW_REQUIRED')
        self.assertEqual(report['automatic_merges'], 0)

    def test_unprovenanced_record_cannot_be_matched(self):
        report = mod.reconcile([{'serial': 'A'}, {'source': 'CMDB', 'serial': 'A'}])
        self.assertEqual(report['candidate_count'], 0)
        self.assertEqual(report['invalid_records'], [{'index': 0, 'reason': 'missing_source'}])
        self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_missing_strong_identity_is_incomplete(self):
        report = mod.reconcile([{'source': 'CMDB', 'name': 'array01'}])
        self.assertEqual(report['invalid_records'][0]['reason'], 'missing_strong_identity')
        self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_placeholders_do_not_produce_false_matches(self):
        report = mod.reconcile([{'source': 'a', 'serial': 'unknown'},
                                {'source': 'b', 'serial': ' UNKNOWN '}])
        self.assertEqual(report['candidate_count'], 0)
        self.assertEqual(len(report['invalid_records']), 2)

    def test_serial_match_but_wwn_conflict_quarantines(self):
        report = mod.reconcile([{'source': 'NetApp', 'serial': 'S1', 'wwn': '5001'},
                                {'source': 'CMDB', 'serial': 's1', 'wwn': '5002'}])
        candidate = report['candidates'][0]
        self.assertEqual(candidate['identity_evidence'], ['serial'])
        self.assertEqual(candidate['identity_conflicts'][0]['field'], 'wwn')
        self.assertEqual(candidate['action'], 'QUARANTINE_IDENTITY_CONFLICT')
        self.assertEqual(report['quarantined_indices'], [0, 1])
        self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_uuid_match_but_serial_conflict_quarantines(self):
        report = mod.reconcile([{'source': 'Pure', 'uuid': 'u', 'serial': 's1'},
                                {'source': 'CMDB', 'uuid': 'U', 'serial': 's2'}])
        self.assertEqual(report['candidates'][0]['identity_conflicts'][0]['field'], 'serial')
        self.assertEqual(report['assessment'], 'INCOMPLETE')

    def test_matching_identifiers_are_not_conflicts(self):
        report = mod.reconcile([{'source': 'a', 'serial': 'S1', 'wwn': 'W1'},
                                {'source': 'b', 'serial': 's1', 'wwn': 'w1'}])
        self.assertEqual(report['candidates'][0]['identity_evidence'], ['serial', 'wwn'])
        self.assertEqual(report['candidates'][0]['identity_conflicts'], [])

    def test_provenance_preserved_without_invented_timestamp(self):
        report = mod.reconcile([{'source': 'Dell', 'serial': 'S', 'collected_at': '2026-10-23T16:00:00Z'},
                                {'source': 'CMDB', 'serial': 'S'}])
        self.assertEqual(report['candidates'][0]['provenance'], [
            {'index': 0, 'source': 'Dell', 'collected_at': '2026-10-23T16:00:00Z'},
            {'index': 1, 'source': 'CMDB', 'collected_at': None},
        ])

    def test_source_data_unchanged_and_deterministic(self):
        records = [{'source': 'a', 'serial': 's', 'wwn': 'a'},
                   {'source': 'b', 'serial': 's', 'wwn': 'b'}]
        before = copy.deepcopy(records)
        self.assertEqual(mod.reconcile(records), mod.reconcile(records))
        self.assertEqual(records, before)

    def test_many_duplicates_fail_closed_before_explosion(self):
        records = [{'source': 's', 'serial': 's'} for _ in range(319)]
        with self.assertRaisesRegex(ValueError, 'candidate pairs'):
            mod.reconcile(records)

    def test_inventory_record_limit(self):
        with self.assertRaisesRegex(ValueError, '10000'):
            mod.reconcile([None] * (mod.MAX_RECORDS + 1))

    def test_cli_does_not_overwrite_and_invalid_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'records.json'
            out = Path(tmp) / 'result.json'
            src.write_text(json.dumps([{'source': 'a', 'serial': 'S'},
                                       {'source': 'b', 'serial': 'S'}]), encoding='utf-8')
            args = [sys.executable, str(SOURCE), str(src), '--output', str(out)]
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = out.read_bytes()
            second = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(out.read_bytes(), original)
            self.assertEqual(json.loads(original)['automatic_merges'], 0)

    def test_cli_incomplete_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'records.json'
            src.write_text('[{"source":"CMDB","name":"array01"}]', encoding='utf-8')
            result = subprocess.run([sys.executable, str(SOURCE), str(src)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['assessment'], 'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
