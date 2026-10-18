import unittest,tempfile,sys,hashlib,json,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from snapshot_restore_v583 import publish_verified_interrupted_stage
from unittest.mock import patch
class ResumeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
  self.stage=self.root/'.storagescope-restore-abc';self.stage.mkdir()
  self.target=self.root/'published'
  name='governance-views.json';data=b'{"ok":true}'
  (self.source/name).write_bytes(data);(self.stage/name).write_bytes(data)
  (self.source/'manifest.json').write_text(json.dumps({'files':[{'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}))
 def run_resume(self):
  with patch('snapshot_restore_v583.verify_backup_snapshot',return_value=True):
   return publish_verified_interrupted_stage(self.stage,self.source,self.target)
 def test_publish_verified_stage(self):
  self.assertTrue(self.run_resume()['resumed']);self.assertTrue(self.target.is_dir());self.assertFalse(self.stage.exists())
 def test_corrupt_stage_preserved(self):
  (self.stage/'governance-views.json').write_bytes(b'bad')
  with self.assertRaises(ValueError):self.run_resume()
  self.assertTrue(self.stage.exists());self.assertFalse(self.target.exists())
 def test_extra_file_rejected(self):
  (self.stage/'extra.txt').write_text('x')
  with self.assertRaises(ValueError):self.run_resume()
 def test_existing_destination_preserved(self):
  self.target.mkdir()
  with self.assertRaises(FileExistsError):self.run_resume()
  self.assertTrue(self.target.exists())
 def test_symlink_stage_rejected(self):
  link=self.root/'.storagescope-restore-link';link.symlink_to(self.stage,target_is_directory=True)
  with patch('snapshot_restore_v583.verify_backup_snapshot',return_value=True):
   with self.assertRaises(ValueError):publish_verified_interrupted_stage(link,self.source,self.target)
 def test_incomplete_stage_rejected(self):
  (self.stage/'governance-views.json').unlink()
  with self.assertRaises(ValueError):self.run_resume()
if __name__=='__main__':unittest.main()
