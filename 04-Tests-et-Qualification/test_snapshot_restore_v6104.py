import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from storagescope_windows import backup_snapshot
from snapshot_restore_v583 import restore_to_empty

class TransactionalRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);data=self.root/'data';data.mkdir()
        (data/'governance-views.json').write_text('original')
        self.snapshot,_=backup_snapshot({'base':data,'decisions':data/'architecture-decisions.sqlite','campaigns':data/'campaigns.sqlite','views':data/'governance-views.json'},self.root/'backups')
        self.target=self.root/'restored'
    def test_atomic_publish(self):
        self.assertTrue(restore_to_empty(self.snapshot,self.target)['restored'])
        self.assertEqual((self.target/'governance-views.json').read_text(),'original')
    def test_no_partial_destination_when_copy_fails(self):
        import snapshot_restore_v583 as mod
        original=mod.os.fsync
        with patch.object(mod.os,'fsync',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):restore_to_empty(self.snapshot,self.target)
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.root.glob('.storagescope-restore-*')))
    def test_existing_target_never_replaced(self):
        self.target.mkdir();(self.target/'keep').write_text('preserve')
        with self.assertRaises(FileExistsError):restore_to_empty(self.snapshot,self.target)
        self.assertEqual((self.target/'keep').read_text(),'preserve')
    def test_missing_parent_refused(self):
        with self.assertRaises(FileExistsError):restore_to_empty(self.snapshot,self.root/'missing'/'restored')
    def test_source_tampering_before_restore_refused(self):
        (self.snapshot/'governance-views.json').write_text('corrupt')
        with self.assertRaises(ValueError):restore_to_empty(self.snapshot,self.target)
        self.assertFalse(self.target.exists())
