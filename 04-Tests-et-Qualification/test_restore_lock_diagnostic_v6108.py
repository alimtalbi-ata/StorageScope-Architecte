import unittest,sys,tempfile,json,os,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from snapshot_restore_v583 import inspect_restore_leases,destination_lease
class Tests(unittest.TestCase):
 def test_active_lock(self):
  with tempfile.TemporaryDirectory() as tmp:
   with destination_lease(Path(tmp)/'out'):
    result=inspect_restore_leases(tmp)
    self.assertEqual(result['locks'][0]['status'],'RECENT')
    self.assertEqual(result['deleted'],0)
 def test_old_lock_only_reviewed(self):
  with tempfile.TemporaryDirectory() as tmp:
   lock=Path(tmp)/'.out.storagescope-restore.lock'
   lock.write_text(json.dumps({'pid':123,'destination':str(Path(tmp)/'out'),'created':1}))
   os.utime(lock,(1,1))
   self.assertEqual(inspect_restore_leases(tmp,now=99999)['locks'][0]['status'],'REVIEW_OLD')
   self.assertTrue(lock.exists())
 def test_invalid_json(self):
  with tempfile.TemporaryDirectory() as tmp:
   (Path(tmp)/'.out.storagescope-restore.lock').write_text('garbage')
   self.assertEqual(inspect_restore_leases(tmp)['locks'][0]['status'],'UNSAFE_ENTRY')
 def test_symlink(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); (root/'other').write_text('secret')
   (root/'.out.storagescope-restore.lock').symlink_to(root/'other')
   self.assertEqual(inspect_restore_leases(root)['locks'][0]['status'],'UNSAFE_ENTRY')
 def test_mismatched_destination(self):
  with tempfile.TemporaryDirectory() as tmp:
   (Path(tmp)/'.out.storagescope-restore.lock').write_text(json.dumps({'pid':1,'destination':str(Path(tmp)/'wrong'),'created':1}))
   self.assertEqual(inspect_restore_leases(tmp)['locks'][0]['status'],'UNSAFE_ENTRY')
 def test_reject_bad_age(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):inspect_restore_leases(tmp,minimum_age_seconds=5)
if __name__=='__main__':unittest.main()
