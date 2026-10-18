import tempfile
import unittest
from pathlib import Path
from storagescope_windows import backup_snapshot
from snapshot_restore_v583 import restore_to_empty

class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.data=self.root/'data'; self.data.mkdir()
        (self.data/'governance-views.json').write_text('{}')
        paths={'base':self.data,'decisions':self.data/'architecture-decisions.sqlite','campaigns':self.data/'campaigns.sqlite','views':self.data/'governance-views.json'}
        self.snapshot,_=backup_snapshot(paths,self.root/'backups')
    def test_restore(self):
        result=restore_to_empty(self.snapshot,self.root/'recovered')
        self.assertTrue(result['restored']);self.assertEqual((self.root/'recovered'/'governance-views.json').read_text(),'{}')
    def test_existing_target_refused(self):
        target=self.root/'recovered';target.mkdir();(target/'keep').write_text('safe')
        with self.assertRaises(FileExistsError):restore_to_empty(self.snapshot,target)
        self.assertEqual((target/'keep').read_text(),'safe')
    def test_tampered_snapshot_refused(self):
        (self.snapshot/'governance-views.json').write_text('tampered')
        with self.assertRaises(ValueError):restore_to_empty(self.snapshot,self.root/'recovered')
        self.assertFalse((self.root/'recovered').exists())
    def test_nested_target_refused(self):
        with self.assertRaises(ValueError):restore_to_empty(self.snapshot,self.snapshot/'recovered')
    def test_symlink_snapshot_refused(self):
        link=self.root/'link';link.symlink_to(self.snapshot,target_is_directory=True)
        with self.assertRaises(ValueError):restore_to_empty(link,self.root/'recovered')
