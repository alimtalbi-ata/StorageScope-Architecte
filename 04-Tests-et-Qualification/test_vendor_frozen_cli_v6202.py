"""V6.202 offline vendor CLI integration tests; synthetic fixtures only.
Author: Abdelhalim Talbi.
"""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / '03-Sources'
sys.path.insert(0, str(SRC))
from storagescope_windows import main
from windows_module_inventory import reachable_modules

GIB = 1073741824


def snapshot():
    return {
        'schema': 'storagescope.vendor-snapshot.v1',
        'vendor': 'netapp_ontap',
        'source_ref': 'synthetic-test-001',
        'collected_at': '2026-10-23T20:00:00Z',
        'systems': [{
            'serial_number': 'S1', 'cluster_name': 'lab',
            'capacity_used_bytes': 20 * GIB,
            'capacity_total_bytes': 100 * GIB,
            'volumes': [{'uuid': 'V1', 'protocol': 'NFS'}],
        }],
    }


class FrozenVendorCLIContractTests(unittest.TestCase):
    def test_vendor_module_in_frozen_static_import_closure(self):
        self.assertIn('vendor_snapshot_import_v6201', reachable_modules(SRC))

    def test_entrypoint_dispatch_is_static_and_does_not_start_gui(self):
        tree = ast.parse((SRC / 'storagescope_windows.py').read_text(encoding='utf-8'))
        fn = next(node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name == 'main')
        self.assertIn('--vendor-snapshot-file', ast.unparse(fn))
        self.assertIn('vendor_snapshot_main', ast.unparse(fn))

    def test_positive_cli_evidence_preserves_input(self):
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td) / 'snapshot.json', Path(td) / 'report.json'
            raw = json.dumps(snapshot(), ensure_ascii=False)
            src.write_text(raw, encoding='utf-8')
            self.assertEqual(main(['--vendor-snapshot-file', str(src), str(out)]), 0)
            report = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(report['schema'], 'storagescope.vendor-import-report.v1')
            self.assertEqual(report['vendor'], 'netapp_ontap')
            self.assertEqual(report['assessment'], 'OBSERVED_ONLY')
            self.assertEqual(report['automatic_changes'], 0)
            self.assertEqual(len(report['topology']['assets']), 1)
            self.assertEqual(src.read_text(encoding='utf-8'), raw)

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td) / 'snapshot.json', Path(td) / 'report.json'
            src.write_text(json.dumps(snapshot()), encoding='utf-8')
            out.write_text('PREEXISTING', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                main(['--vendor-snapshot-file', str(src), str(out)])
            self.assertEqual(out.read_text(encoding='utf-8'), 'PREEXISTING')

    def test_ambiguous_json_fails_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td) / 'snapshot.json', Path(td) / 'report.json'
            src.write_text('{"schema":"storagescope.vendor-snapshot.v1","vendor":"netapp_ontap","vendor":"pure_flashblade"}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
                main(['--vendor-snapshot-file', str(src), str(out)])
            self.assertFalse(out.exists())


    def test_unsupported_vendor_fails_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td) / 'snapshot.json', Path(td) / 'report.json'
            data = snapshot()
            data['vendor'] = 'unrecognized_vendor'
            src.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unsupported vendor'):
                main(['--vendor-snapshot-file', str(src), str(out)])
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
