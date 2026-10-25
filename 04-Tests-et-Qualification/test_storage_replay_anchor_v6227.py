"""V6.227 nested ledger-backup-domain anchor regression tests.
Author: Abdelhalim Talbi.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_replay_anchor_v6225 import create_anchor, verify_anchor
from storage_replay_ledger_v6222 import initialize_ledger


class AnchorDomainTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.ledger_dir = root / 'ledger'
        self.ledger_dir.mkdir()
        self.protected = root / 'protected'
        self.protected.mkdir()
        self.ledger = self.ledger_dir / 'replay.sqlite'
        self.anchor = self.protected / 'checkpoint.json'
        env = patch.dict(os.environ, {
            'STORAGESCOPE_REPLAY_ANCHOR_KEY': bytes(range(32)).hex()
        })
        env.start()
        self.addCleanup(env.stop)
        initialize_ledger(self.ledger)
        create_anchor(self.ledger, self.anchor)

    def test_sibling_protected_checkpoint_remains_valid(self):
        self.assertEqual(verify_anchor(self.ledger, self.anchor)['integrity'], 'PASS')

    def test_create_rejects_nested_ledger_directory(self):
        nested = self.ledger_dir / 'backups'
        nested.mkdir()
        target = nested / 'checkpoint.json'
        with self.assertRaisesRegex(ValueError, 'outside ledger directory'):
            create_anchor(self.ledger, target)
        self.assertFalse(target.exists())

    def test_verify_rejects_nested_ledger_directory(self):
        nested = self.ledger_dir / 'backups'
        nested.mkdir()
        target = nested / 'checkpoint.json'
        target.write_bytes(self.anchor.read_bytes())
        with self.assertRaisesRegex(ValueError, 'outside ledger directory'):
            verify_anchor(self.ledger, target)

    def test_normalized_traversal_into_ledger_directory_rejected(self):
        nested = self.ledger_dir / 'backups'
        nested.mkdir()
        target = self.protected / '..' / 'ledger' / 'backups' / 'checkpoint.json'
        with self.assertRaisesRegex(ValueError, 'outside ledger directory'):
            create_anchor(self.ledger, target)
        self.assertFalse((nested / 'checkpoint.json').exists())


if __name__ == '__main__':
    unittest.main()
