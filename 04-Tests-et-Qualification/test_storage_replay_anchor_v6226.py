"""V6.226 synthetic filesystem/JSON ambiguity regressions.
Author: Abdelhalim Talbi.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storage_replay_anchor_v6225 import create_anchor, verify_anchor
from storage_replay_ledger_v6222 import initialize_ledger


class AnchorHardeningTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / 'ledger').mkdir()
        (root / 'protected').mkdir()
        self.ledger = root / 'ledger' / 'replay.sqlite'
        self.anchor = root / 'protected' / 'checkpoint.json'
        env = patch.dict(os.environ, {
            'STORAGESCOPE_REPLAY_ANCHOR_KEY': bytes(range(32)).hex()
        })
        env.start()
        self.addCleanup(env.stop)
        initialize_ledger(self.ledger)
        create_anchor(self.ledger, self.anchor)

    def test_canonical_anchor_still_valid(self):
        self.assertEqual(verify_anchor(self.ledger, self.anchor)['integrity'], 'PASS')

    def test_duplicate_json_key_rejected(self):
        original = self.anchor.read_bytes()
        self.anchor.write_bytes(b'{"schema":"storagescope.replay-anchor.v1",' + original[1:])
        with self.assertRaisesRegex(ValueError, 'ROLLBACK_OR_TAMPERING'):
            verify_anchor(self.ledger, self.anchor)

    def test_noncanonical_json_rejected(self):
        parsed = json.loads(self.anchor.read_bytes())
        self.anchor.write_text(json.dumps(parsed, indent=2) + '\n', encoding='ascii')
        with self.assertRaisesRegex(ValueError, 'ROLLBACK_OR_TAMPERING'):
            verify_anchor(self.ledger, self.anchor)

    def test_hardlinked_anchor_rejected(self):
        alias = self.anchor.with_name('hardlink.json')
        try:
            os.link(self.anchor, alias)
        except (OSError, NotImplementedError) as exc:
            self.skipTest('hardlinks unavailable: ' + str(exc))
        with self.assertRaisesRegex(ValueError, 'independent regular file'):
            verify_anchor(self.ledger, self.anchor)

    def test_symlink_grandparent_rejected(self):
        protected = self.anchor.parent
        nested = protected / 'nested'
        nested.mkdir()
        (nested / 'checkpoint.json').write_bytes(self.anchor.read_bytes())
        alias = protected.parent / 'alias'
        try:
            alias.symlink_to(protected, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest('symlinks unavailable: ' + str(exc))
        with self.assertRaisesRegex(ValueError, 'symlink'):
            verify_anchor(self.ledger, alias / 'nested' / 'checkpoint.json')


if __name__ == '__main__':
    unittest.main()
