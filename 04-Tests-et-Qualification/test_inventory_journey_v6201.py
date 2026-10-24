"""End-to-end offline NAS inventory acceptance, using representative synthetic data.

This tests the actual file reader and normalizer, not a live Windows GUI.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from vendor_snapshot_import_v6201 import load_snapshot, normalize

GIB = 1073741824


class InventoryJourneyTests(unittest.TestCase):
    def test_import_multi_system_multi_protocol_and_quarantine(self):
        data = {
            'schema': 'storagescope.vendor-snapshot.v1',
            'vendor': 'netapp_ontap',
            'source_ref': 'qualification-lab-01',
            'collected_at': '2026-10-24T10:00:00Z',
            'systems': [
                {'serial_number': 'ONTAP-001', 'cluster_name': 'nas-paris',
                 'capacity_used_bytes': 80 * GIB, 'capacity_total_bytes': 100 * GIB,
                 'volumes': [
                     {'uuid': 'vol-nfs', 'protocol': 'NFS', 'used_bytes': 10 * GIB, 'quota_bytes': 20 * GIB},
                     {'uuid': 'vol-smb', 'protocol': 'SMB', 'used_bytes': 5 * GIB, 'quota_bytes': 10 * GIB},
                 ]},
                {'serial_number': 'ONTAP-002', 'cluster_name': 'nas-lyon',
                 'capacity_used_bytes': 20 * GIB, 'capacity_total_bytes': 50 * GIB,
                 'volumes': []},
                {'serial_number': 'ONTAP-003', 'cluster_name': 'nas-invalid',
                 'capacity_used_bytes': 60 * GIB, 'capacity_total_bytes': 50 * GIB,
                 'volumes': []},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'snapshot.json'
            source.write_text(json.dumps(data), encoding='utf-8')
            original = source.read_bytes()
            result = normalize(load_snapshot(source))
            self.assertEqual(source.read_bytes(), original)
        self.assertEqual(result['assessment'], 'INCOMPLETE')
        self.assertEqual(result['automatic_changes'], 0)
        self.assertEqual(len(result['topology']['assets']), 2)
        self.assertEqual(len(result['topology']['shares']), 2)
        self.assertEqual({s['protocol'] for s in result['topology']['shares']}, {'NFS', 'SMB'})
        self.assertTrue(any('inconsistent capacity' in issue for issue in result['rejected']))
        self.assertEqual(result['topology']['assets'][0]['id'], 'netapp_ontap:ONTAP-001')
        self.assertEqual({s['nas_id'] for s in result['topology']['shares']},
                         {'netapp_ontap:ONTAP-001'})

    def test_invalid_json_never_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'duplicate.json'
            source.write_text('{"schema":"a","schema":"b"}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
                normalize(load_snapshot(source))


if __name__ == '__main__':
    unittest.main()
