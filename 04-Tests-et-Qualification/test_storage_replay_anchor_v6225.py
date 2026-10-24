"""Synthetic local tests for operator-managed anti-rollback checkpoint V6.225."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_replay_anchor_v6225 import create_anchor, verify_anchor
from storage_replay_ledger_v6222 import initialize_ledger, register_snapshot
from test_storage_replay_ledger_v6222 import SECRET, snapshot


class ReplayAnchorTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / 'ledger').mkdir()
        (root / 'protected').mkdir()
        self.ledger = root / 'ledger' / 'replay.sqlite'
        self.anchor = root / 'protected' / 'checkpoint.json'
        env = patch.dict(os.environ, {
            'STORAGESCOPE_HMAC_KEY_KEY_A': SECRET.hex(),
            'STORAGESCOPE_REPLAY_ANCHOR_KEY': bytes(range(32, 64)).hex(),
        })
        env.start()
        self.addCleanup(env.stop)
        initialize_ledger(self.ledger)

    def test_create_verify_and_readonly(self):
        register_snapshot(snapshot(), self.ledger)
        before = hashlib.sha256(self.ledger.read_bytes()).digest()
        self.assertEqual(create_anchor(self.ledger, self.anchor)['status'], 'ANCHOR_CREATED')
        self.assertEqual(verify_anchor(self.ledger, self.anchor)['integrity'], 'PASS')
        self.assertEqual(before, hashlib.sha256(self.ledger.read_bytes()).digest())
        contents = self.anchor.read_text()
        self.assertNotIn('collector:a', contents)
        self.assertNotIn(SECRET.hex(), contents)

    def test_restored_older_ledger_is_rejected(self):
        register_snapshot(snapshot(), self.ledger)
        previous = self.ledger.with_suffix('.backup')
        shutil.copy2(self.ledger, previous)
        register_snapshot(snapshot(), self.ledger)
        create_anchor(self.ledger, self.anchor)
        shutil.copy2(previous, self.ledger)
        with self.assertRaisesRegex(ValueError, 'ROLLBACK_OR_TAMPERING'):
            verify_anchor(self.ledger, self.anchor)

    def test_changed_row_rejected_even_if_count_same(self):
        register_snapshot(snapshot(), self.ledger)
        create_anchor(self.ledger, self.anchor)
        with closing(sqlite3.connect(self.ledger)) as db:
            with db:
                db.execute('UPDATE collection_seen SET observation_count=observation_count+1')
        with self.assertRaisesRegex(ValueError, 'ROLLBACK_OR_TAMPERING'):
            verify_anchor(self.ledger, self.anchor)

    def test_new_collection_requires_new_versioned_anchor(self):
        create_anchor(self.ledger, self.anchor)
        register_snapshot(snapshot(), self.ledger)
        with self.assertRaisesRegex(ValueError, 'ROLLBACK_OR_TAMPERING'):
            verify_anchor(self.ledger, self.anchor)
        with self.assertRaises(FileExistsError):
            create_anchor(self.ledger, self.anchor)
        new_anchor = self.anchor.with_name('checkpoint-2.json')
        create_anchor(self.ledger, new_anchor)
        self.assertEqual(verify_anchor(self.ledger, new_anchor)['registered_collections'], 1)

    def test_anchor_missing_or_forged_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            verify_anchor(self.ledger, self.anchor)
        create_anchor(self.ledger, self.anchor)
        data = json.loads(self.anchor.read_text())
        data['ledger_mac_sha256'] = '0' * 64
        self.anchor.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'ROLLBACK_OR_TAMPERING'):
            verify_anchor(self.ledger, self.anchor)

    def test_key_unavailable_or_wrong_rejected(self):
        with patch.dict(os.environ, {'STORAGESCOPE_REPLAY_ANCHOR_KEY': ''}):
            with self.assertRaisesRegex(ValueError, 'operator key'):
                create_anchor(self.ledger, self.anchor)
        self.assertFalse(self.anchor.exists())
        create_anchor(self.ledger, self.anchor)
        with patch.dict(os.environ, {'STORAGESCOPE_REPLAY_ANCHOR_KEY': 'ff' * 32}):
            with self.assertRaisesRegex(ValueError, 'ROLLBACK_OR_TAMPERING'):
                verify_anchor(self.ledger, self.anchor)

    def test_anchor_must_be_separate_and_never_overwritten(self):
        with self.assertRaisesRegex(ValueError, 'outside ledger directory'):
            create_anchor(self.ledger, self.ledger.parent / 'checkpoint.json')
        create_anchor(self.ledger, self.anchor)
        before = self.anchor.read_bytes()
        with self.assertRaises(FileExistsError):
            create_anchor(self.ledger, self.anchor)
        self.assertEqual(before, self.anchor.read_bytes())

    def test_malformed_interior_ledger_row_rejected(self):
        with closing(sqlite3.connect(self.ledger)) as db:
            with db:
                db.execute('INSERT INTO collection_seen VALUES (?, ?, ?, ?)',
                           ('collector:a', str(uuid4()), 1, 'invalid-time'))
        with self.assertRaisesRegex(ValueError, 'invalid UTC timestamp'):
            create_anchor(self.ledger, self.anchor)
        self.assertFalse(self.anchor.exists())

    def test_cli_checkpoint_and_verify(self):
        script = Path(__file__).resolve().parents[1] / '03-Sources' / 'storagescope_windows.py'
        for command, status in (('--storage-replay-anchor-create', 'ANCHOR_CREATED'),
                                ('--storage-replay-anchor-check', 'VERIFIED')):
            result = subprocess.run([sys.executable, str(script), command,
                                     str(self.ledger), str(self.anchor)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], status)


if __name__ == '__main__':
    unittest.main()
