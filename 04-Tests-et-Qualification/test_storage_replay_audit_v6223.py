"""V6.223 read-only replay ledger audit qualification (synthetic)."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_replay_ledger_v6222 import initialize_ledger, inspect_ledger, register_snapshot
from test_storage_replay_ledger_v6222 import SECRET, snapshot


class ReplayAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ledger = self.root / 'ledger.sqlite'
        env = patch.dict(os.environ, {'STORAGESCOPE_HMAC_KEY_KEY_A': SECRET.hex()})
        env.start()
        self.addCleanup(env.stop)

    def test_missing_ledger_not_initialized_by_audit(self):
        with self.assertRaisesRegex(ValueError, 'explicit initialization'):
            inspect_ledger(self.ledger)
        self.assertFalse(self.ledger.exists())

    def test_empty_ledger_audit_is_read_only(self):
        initialize_ledger(self.ledger)
        before = hashlib.sha256(self.ledger.read_bytes()).hexdigest()
        info = inspect_ledger(self.ledger)
        self.assertEqual(info['status'], 'READ_ONLY')
        self.assertEqual(info['registered_collections'], 0)
        self.assertEqual(info['registered_observations'], 0)
        self.assertEqual(info['distinct_sources'], 0)
        self.assertIsNone(info['first_accepted_utc'])
        self.assertEqual(before, hashlib.sha256(self.ledger.read_bytes()).hexdigest())

    def test_audit_after_two_collections_no_write_or_identity_leak(self):
        initialize_ledger(self.ledger)
        register_snapshot(snapshot(), self.ledger)
        register_snapshot(snapshot(), self.ledger)
        before = hashlib.sha256(self.ledger.read_bytes()).hexdigest()
        info = inspect_ledger(self.ledger)
        self.assertEqual(info['registered_collections'], 2)
        self.assertEqual(info['registered_observations'], 2)
        self.assertEqual(info['distinct_sources'], 1)
        self.assertTrue(info['first_accepted_utc'].endswith('+00:00'))
        self.assertNotIn('collector:a', repr(info))
        self.assertNotIn(SECRET.hex(), repr(info))
        self.assertEqual(before, hashlib.sha256(self.ledger.read_bytes()).hexdigest())

    def test_forged_schema_rejected_without_modification(self):
        with sqlite3.connect(self.ledger) as db:
            db.execute('PRAGMA user_version=1')
            db.execute('CREATE TABLE collection_seen (source_ref TEXT, collection_id TEXT, observation_count INTEGER, accepted_utc TEXT)')
        before = hashlib.sha256(self.ledger.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'primary key'):
            inspect_ledger(self.ledger)
        self.assertEqual(before, hashlib.sha256(self.ledger.read_bytes()).hexdigest())

    def test_audit_cli_json(self):
        initialize_ledger(self.ledger)
        script = Path(__file__).resolve().parents[1] / '03-Sources' / 'storagescope_windows.py'
        cmd = [sys.executable, str(script), '--storage-replay-audit', str(self.ledger)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['integrity'], 'PASS')
        self.assertEqual(json.loads(result.stdout)['automatic_changes'], 0)


if __name__ == '__main__':
    unittest.main()
