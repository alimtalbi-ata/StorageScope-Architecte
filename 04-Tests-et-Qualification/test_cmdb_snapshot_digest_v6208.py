"""V6.208 — exact-byte CMDB snapshot evidence (synthetic fixtures only).

Author: Abdelhalim Talbi.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from cmdb_review_desktop_v6198 import (export_cmdb_report, format_cmdb_report,
                                       review_cmdb_file)


class ExactCMDBDigestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'cmdb.json'

    def test_digest_matches_exact_bytes_including_bom_and_whitespace(self):
        raw = b'\xef\xbb\xbf [ { "source": "NetApp", "serial": "S-1" } ]\n'
        self.path.write_bytes(raw)
        report = review_cmdb_file(self.path)
        self.assertEqual(report['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(report['snapshot_size_bytes'], len(raw))
        self.assertEqual(report['assessment'], 'NO_CANDIDATES')
        self.assertIn(report['snapshot_sha256'], format_cmdb_report(report))
        self.assertEqual(self.path.read_bytes(), raw)

    def test_equivalent_json_with_different_source_bytes_has_distinct_digest(self):
        raw1 = b'[ {"source":"CMDB", "serial":"S-1"} ]'
        raw2 = b'[{"source":"CMDB","serial":"S-1"}]'
        self.path.write_bytes(raw1)
        first = review_cmdb_file(self.path)
        self.path.write_bytes(raw2)
        second = review_cmdb_file(self.path)
        self.assertNotEqual(first['snapshot_sha256'], second['snapshot_sha256'])
        self.assertEqual(first['candidate_count'], second['candidate_count'])

    def test_export_persists_source_digest_and_does_not_overwrite(self):
        raw = (b'[{"source":"NetApp","serial":"S-1"},'
               b'{"source":"CMDB","serial":"S-1"}]')
        self.path.write_bytes(raw)
        output = self.path.parent / 'evidence.json'
        report = export_cmdb_report(self.path, output)
        stored = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(stored['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(stored['snapshot_size_bytes'], len(raw))
        self.assertEqual(stored['automatic_merges'], 0)
        self.assertEqual(stored['candidate_count'], 1)
        self.assertEqual(report, stored)
        prior = output.read_bytes()
        with self.assertRaises(FileExistsError):
            export_cmdb_report(self.path, output)
        self.assertEqual(output.read_bytes(), prior)

    def test_invalid_json_does_not_produce_evidence_report(self):
        self.path.write_bytes(b'[{"source":"x","source":"y","serial":"S"}]')
        output = self.path.parent / 'not-created.json'
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON property'):
            export_cmdb_report(self.path, output)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
