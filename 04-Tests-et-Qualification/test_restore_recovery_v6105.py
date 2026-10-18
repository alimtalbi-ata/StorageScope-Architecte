import os
import tempfile
import unittest
from pathlib import Path
from snapshot_restore_v583 import inspect_interrupted_restores

class RecoveryInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def test_empty(self):
        self.assertEqual(inspect_interrupted_restores(self.root)['stages'],[])
    def test_recent_stage_is_not_marked_old(self):
        (self.root/'.storagescope-restore-recent').mkdir()
        self.assertEqual(inspect_interrupted_restores(self.root)['stages'][0]['status'],'RECENT')
    def test_old_stage_is_only_reported(self):
        stage=self.root/'.storagescope-restore-old';stage.mkdir();(stage/'data').write_text('keep')
        os.utime(stage,(100,100))
        result=inspect_interrupted_restores(self.root,now=4000)
        self.assertEqual(result['stages'][0]['status'],'REVIEW_OLD')
        self.assertEqual(result['deleted'],0)
        self.assertTrue((stage/'data').exists())
    def test_unrelated_directory_is_ignored(self):
        (self.root/'other').mkdir()
        self.assertEqual(inspect_interrupted_restores(self.root)['stages'],[])
    def test_symlink_stage_is_not_followed(self):
        target=self.root/'important';target.mkdir()
        link=self.root/'.storagescope-restore-link'
        try:link.symlink_to(target,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('symlinks unsupported')
        self.assertEqual(inspect_interrupted_restores(self.root)['stages'][0]['status'],'UNSAFE_ENTRY')
        self.assertTrue(target.exists())
    def test_short_age_rejected(self):
        with self.assertRaises(ValueError):inspect_interrupted_restores(self.root,minimum_age_seconds=0)
    def test_parent_symlink_rejected(self):
        link=self.root.parent/(self.root.name+'-link')
        try:link.symlink_to(self.root,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('symlinks unsupported')
        try:
            with self.assertRaises(ValueError):inspect_interrupted_restores(link)
        finally:link.unlink()
