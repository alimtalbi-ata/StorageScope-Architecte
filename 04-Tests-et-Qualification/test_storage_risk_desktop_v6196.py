"""Regression tests for the read-only desktop SAN/NAS risk integration."""
import json
import pathlib
import sys
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / '03-Sources'
sys.path.insert(0, str(SOURCE))
from storage_risk_desktop_v6196 import (MAX_INPUT_BYTES, assess_topology_file,
                                        export_risk_report, format_risk_report)


def topology():
    return {'schema': 'storagescope.storage-topology.v1',
            'assets': [{'id': 'host1', 'kind': 'host'},
                       {'id': 'array1', 'kind': 'storage_array', 'used_gib': 97, 'total_gib': 100}],
            'paths': [{'host_id': 'host1', 'storage_id': 'array1', 'fabric': 'A', 'state': 'up'}],
            'shares': []}


class DesktopRiskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.source = self.root / 'topology.json'

    def put(self, text):
        self.source.write_bytes(text if isinstance(text, bytes) else text.encode('utf-8'))

    def test_real_risk_engine_reports_single_fabric_and_capacity(self):
        self.put(json.dumps(topology()))
        before = self.source.read_bytes()
        report = assess_topology_file(self.source)
        self.assertEqual(report['assessment'], 'RISKS_FOUND')
        self.assertIn('SINGLE_ACTIVE_FABRIC', {f['code'] for f in report['findings']})
        self.assertIn('CAPACITY_CRITICAL', {f['code'] for f in report['findings']})
        self.assertEqual(report['automatic_changes'], 0)
        self.assertEqual(before, self.source.read_bytes())

    def test_bom_utf8_accepted(self):
        self.put(b'\xef\xbb\xbf' + json.dumps(topology()).encode('utf-8'))
        self.assertEqual(assess_topology_file(self.source)['assets'], 2)

    def test_duplicate_json_key_rejected_fail_closed(self):
        self.put('{"schema":"storagescope.storage-topology.v1","assets":[],"assets":[],"paths":[],"shares":[]}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON property'):
            assess_topology_file(self.source)

    def test_non_finite_json_rejected(self):
        self.put('{"schema":"storagescope.storage-topology.v1","assets":[{"id":"x","kind":"nas","used_gib":NaN}],"paths":[],"shares":[]}')
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            assess_topology_file(self.source)

    def test_invalid_json_rejected(self):
        self.put('{broken')
        with self.assertRaises(ValueError):
            assess_topology_file(self.source)

    def test_invalid_encoding_rejected(self):
        self.put(b'\xff\xfe\xfa')
        with self.assertRaises(ValueError):
            assess_topology_file(self.source)

    def test_empty_input_rejected(self):
        self.put(b'')
        with self.assertRaisesRegex(ValueError, 'empty'):
            assess_topology_file(self.source)

    def test_oversized_input_rejected(self):
        self.put(b' ' * (MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, '8 MiB'):
            assess_topology_file(self.source)

    def test_missing_file_rejected(self):
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            assess_topology_file(self.source)

    def test_render_preserves_incomplete_status(self):
        self.put(json.dumps({'schema': 'storagescope.storage-topology.v1', 'assets': [], 'paths': [], 'shares': []}))
        report = assess_topology_file(self.source)
        rendered = format_risk_report(report)
        self.assertIn('INCOMPLETE', rendered)
        self.assertIn('TOPOLOGY_EMPTY', rendered)
        self.assertIn('Aucune modification CMDB', rendered)

    def test_render_rejects_invalid_limit(self):
        with self.assertRaises(ValueError):
            format_risk_report({'findings': []}, limit=True)

    def test_export_creates_new_file_and_never_overwrites(self):
        self.put(json.dumps(topology()))
        output = self.root / 'risk-report.json'
        report = export_risk_report(self.source, output)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['findings'], report['findings'])
        original = output.read_bytes()
        with self.assertRaises(FileExistsError):
            export_risk_report(self.source, output)
        self.assertEqual(original, output.read_bytes())
        self.assertEqual(json.loads(self.source.read_text())['schema'], topology()['schema'])

    def test_export_refuses_source_as_destination(self):
        self.put(json.dumps(topology()))
        original = self.source.read_bytes()
        with self.assertRaises(FileExistsError):
            export_risk_report(self.source, self.source)
        self.assertEqual(self.source.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
