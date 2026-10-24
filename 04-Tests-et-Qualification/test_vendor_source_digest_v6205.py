"""V6.205: exact-byte snapshot provenance; all fixtures synthetic.
Author: Abdelhalim Talbi.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '03-Sources'))
from vendor_snapshot_import_v6201 import MAX_BYTES, load_snapshot, load_snapshot_with_digest, main, normalize


def sample():
    return {'schema': 'storagescope.vendor-snapshot.v1', 'vendor': 'netapp_ontap',
            'source_ref': 'synthetic-v6205', 'collected_at': '2026-10-24T00:00:00Z',
            'systems': [{'serial_number': 'NAS-01', 'capacity_used_bytes': 1,
                         'capacity_total_bytes': 100, 'volumes': []}]}


class ExactSourceDigestTests(unittest.TestCase):
    def test_cli_digest_matches_original_bytes_including_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp)/'snapshot.json', Path(tmp)/'report.json'
            raw = b'\xef\xbb\xbf' + json.dumps(sample(), indent=2).encode('utf-8')
            source.write_bytes(raw)
            self.assertEqual(main([str(source), str(out)]), 0)
            report = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(report['snapshot_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(report['automatic_changes'], 0)
            self.assertEqual(report['assessment'], 'OBSERVED_ONLY')
            with self.assertRaises(FileExistsError):
                main([str(source), str(out)])

    def test_digest_is_of_raw_bytes_not_canonical_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'source.json'
            digests = []
            for indent in (None, 4):
                raw = json.dumps(sample(), indent=indent).encode('utf-8')
                path.write_bytes(raw)
                data, digest = load_snapshot_with_digest(path)
                self.assertEqual(data, sample())
                self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
                self.assertEqual(load_snapshot(path), sample())
                self.assertEqual(normalize(data, source_sha256=digest)['snapshot_sha256'], digest)
                digests.append(digest)
            self.assertNotEqual(*digests)

    def test_duplicate_keys_fail_before_digest_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'duplicate.json'
            path.write_bytes(b'{"vendor":"netapp_ontap","vendor":"pure_flashblade"}')
            with self.assertRaisesRegex(ValueError, 'Duplicate JSON property'):
                load_snapshot_with_digest(path)

    def test_oversized_file_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp)/'huge.json', Path(tmp)/'report.json'
            source.write_bytes(b' '*(MAX_BYTES+1))
            with self.assertRaisesRegex(ValueError, 'exceeds 5 MB'):
                main([str(source), str(out)])
            self.assertFalse(out.exists())

    def test_invalid_caller_supplied_digest_rejected(self):
        for bad in ('x'*64, '0'*63, 'F'*64, 3):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, 'Invalid source SHA-256'):
                    normalize(sample(), source_sha256=bad)

    def test_windows_desktop_uses_same_exact_byte_digest(self):
        src = (ROOT/'03-Sources/storagescope_windows.py').read_text(encoding='utf-8')
        handler = src.split('        def review_vendor_snapshot():', 1)[1].split('        ttk.Button(page, text=', 1)[0]
        self.assertIn('load_snapshot_with_digest(chosen)', handler)
        self.assertIn('normalize(snapshot, source_sha256=digest)', handler)
        self.assertIn('SHA-256 du fichier source', handler)

    def test_windows_artifact_source_label_never_uses_stale_version(self):
        workflow = (ROOT/'.github/workflows/windows-build.yml').read_text(encoding='utf-8')
        self.assertIn('StorageScope-SOURCES-EXACT-HEAD.zip', workflow)
        self.assertIn('name: StorageScope-SOURCES-EXACT-HEAD', workflow)
        self.assertNotIn('StorageScope-SOURCES-V6203', workflow)
        self.assertNotIn('StorageScope-V6.203-SOURCES-EXACT-HEAD.zip', workflow)
        self.assertIn('Frozen executable source digest does not match', workflow)


if __name__ == '__main__':
    unittest.main()
