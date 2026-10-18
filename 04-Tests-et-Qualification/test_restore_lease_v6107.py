import unittest,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from snapshot_restore_v583 import destination_lease
class LeaseTests(unittest.TestCase):
 def test_lease_lifecycle(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'out';lock=Path(tmp)/'.out.storagescope-restore.lock'
   with destination_lease(target):
    self.assertTrue(lock.exists())
    with self.assertRaises(FileExistsError):
     with destination_lease(target):pass
   self.assertFalse(lock.exists())
 def test_existing_lock_is_not_deleted(self):
  with tempfile.TemporaryDirectory() as tmp:
   lock=Path(tmp)/'.out.storagescope-restore.lock';lock.write_text('another process')
   with self.assertRaises(FileExistsError):
    with destination_lease(Path(tmp)/'out'):pass
   self.assertEqual(lock.read_text(),'another process')
 def test_exception_releases_lease(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'out'
   with self.assertRaisesRegex(RuntimeError,'failure'):
    with destination_lease(target):raise RuntimeError('failure')
   self.assertFalse((Path(tmp)/'.out.storagescope-restore.lock').exists())
if __name__=='__main__':unittest.main()
