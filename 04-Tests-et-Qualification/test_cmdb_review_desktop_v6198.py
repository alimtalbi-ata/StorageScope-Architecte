"""Read-only desktop CMDB review regression tests. Author: Abdelhalim Talbi."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / '03-Sources'
sys.path.insert(0, str(SOURCE))
from cmdb_review_desktop_v6198 import (MAX_INPUT_BYTES, review_cmdb_file,
                                       format_cmdb_report, export_cmdb_report)


class CMDBDesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'inventory.json'

    def put(self, content):
        self.source.write_bytes(content if isinstance(content, bytes) else content.encode('utf-8'))

    def test_identity_conflict_visible_in_desktop(self):
        records = [{'source': 'NetApp', 'serial': 'S1', 'wwn': '5001'},
                   {'source': 'CMDB', 'serial': 'S1', 'wwn': '5002'}]
        self.put(json.dumps(records))
        before = self.source.read_bytes()
        report = review_cmdb_file(self.source)
        self.assertEqual(report['assessment'], 'INCOMPLETE')
        self.assertEqual(report['quarantined_indices'], [0, 1])
        self.assertIn('Identité contradictoire : wwn', format_cmdb_report(report))
        self.assertEqual(before, self.source.read_bytes())

    def test_missing_source_remains_incomplete(self):
        self.put('[{"serial":"S1"},{"source":"CMDB","serial":"S1"}]')
        report = review_cmdb_file(self.source)
        self.assertEqual(report['candidate_count'], 0)
        self.assertIn('INVALIDE', format_cmdb_report(report))

    def test_bom_utf8_supported(self):
        self.put(b'\xef\xbb\xbf' + b'[ {"source":"a","serial":"S"} ]')
        self.assertEqual(review_cmdb_file(self.source)['records'], 1)

    def test_duplicate_keys_rejected(self):
        self.put('[{"source":"a","source":"b","serial":"S"}]')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON property'):
            review_cmdb_file(self.source)

    def test_non_finite_rejected(self):
        self.put('[{"source":"a","serial":"S","capacity":NaN}]')
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            review_cmdb_file(self.source)

    def test_invalid_encoding_rejected(self):
        self.put(b'\xff\xfe')
        with self.assertRaises(ValueError):
            review_cmdb_file(self.source)

    def test_missing_file_rejected(self):
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            review_cmdb_file(self.source)

    def test_oversized_file_rejected(self):
        self.put(b' ' * (MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, '8 MiB'):
            review_cmdb_file(self.source)

    def test_empty_file_rejected(self):
        self.put(b'')
        with self.assertRaisesRegex(ValueError, 'empty'):
            review_cmdb_file(self.source)

    def test_export_no_overwrite(self):
        self.put('[{"source":"a","serial":"S"}]')
        output = self.source.parent / 'report.json'
        report = export_cmdb_report(self.source, output)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['records'], report['records'])
        before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            export_cmdb_report(self.source, output)
        self.assertEqual(before, output.read_bytes())

    def test_export_refuses_input_as_output(self):
        self.put('[{"source":"a","serial":"S"}]')
        before = self.source.read_bytes()
        with self.assertRaises(FileExistsError):
            export_cmdb_report(self.source, self.source)
        self.assertEqual(before, self.source.read_bytes())

    def test_bounded_display_never_hides_totals(self):
        self.put(json.dumps([{'source': 'a', 'serial': 'S'},
                             {'source': 'b', 'serial': 'S'},
                             {'source': 'c', 'serial': 'S'}]))
        rendered = format_cmdb_report(review_cmdb_file(self.source), limit=1)
        self.assertIn('Candidats à revue : 3', rendered)
        self.assertIn('2 candidats supplémentaires non affichés', rendered)

    def test_invalid_display_limit_rejected(self):
        with self.assertRaises(ValueError):
            format_cmdb_report({}, limit=True)

    def test_windows_entrypoint_cli_exports_review_only(self):
        from storagescope_windows import main
        self.put('[{"source":"a","serial":"S"},{"source":"b","serial":"S"}]')
        output = self.source.parent / 'frozen-cmdb.json'
        self.assertEqual(main(['--cmdb-review-file', str(self.source), str(output)]), 0)
        result = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(result['candidate_count'], 1)
        self.assertEqual(result['automatic_merges'], 0)
        with self.assertRaises(FileExistsError):
            main(['--cmdb-review-file', str(self.source), str(output)])

    def test_pyinstaller_import_closure_contains_cmdb(self):
        from windows_module_inventory import reachable_modules
        reachable = reachable_modules(SOURCE)
        self.assertIn('cmdb_review_desktop_v6198', reachable)
        self.assertIn('inventory_reconcile_v619', reachable)

    def test_reconcile_bounded_pairs(self):
        self.put(json.dumps([{'source': 'a', 'serial': 'S'} for _ in range(319)]))
        with self.assertRaisesRegex(ValueError, 'candidate pairs'):
            review_cmdb_file(self.source)


if __name__ == '__main__':
    unittest.main()
