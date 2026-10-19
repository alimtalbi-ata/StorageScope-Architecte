"""Restore staging safety tests. Author: Abdelhalim Talbi."""
import sys,tempfile,unittest,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"03-Sources"))
from storagescope_windows import application_paths,backup_snapshot
from restore_staging import stage_verified_restore
class RestoreStagingTests(unittest.TestCase):
 def test_requires_confirmation(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(PermissionError):
    stage_verified_restore(Path(tmp)/"missing",Path(tmp)/"data")
 def test_stage_preserves_active(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);paths=application_paths(root/"original")
   paths["views"].write_text('{"saved":true}',encoding="utf-8")
   snapshot,_=backup_snapshot(paths,root/"archives")
   live=root/"active";live.mkdir();(live/"governance-views.json").write_text('{"live":true}')
   stage=stage_verified_restore(snapshot,live,confirm=True)
   self.assertEqual((stage/"governance-views.json").read_text(),'{"saved":true}')
   self.assertEqual((live/"governance-views.json").read_text(),'{"live":true}')
 def test_staged_digest_matches_snapshot(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);paths=application_paths(root/'original')
   paths['views'].write_text('test snapshot',encoding='utf-8')
   snapshot,_=backup_snapshot(paths,root/'archives')
   stage=stage_verified_restore(snapshot,root/'active',confirm=True)
   source_hash=hashlib.sha256((snapshot/'governance-views.json').read_bytes()).hexdigest()
   stage_hash=hashlib.sha256((stage/'governance-views.json').read_bytes()).hexdigest()
   self.assertEqual(source_hash,stage_hash)
 def test_corruption_during_copy_cleans_staging(self):
  from unittest.mock import patch
  import restore_staging
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);paths=application_paths(root/'original')
   paths['views'].write_text('known-good',encoding='utf-8')
   snapshot,_=backup_snapshot(paths,root/'archives')
   active=root/'active'
   real_digest=restore_staging.hashlib.file_digest
   def corrupt_digest(handle,algorithm):
    result=real_digest(handle,algorithm)
    if 'storagescope-restore-' in str(getattr(handle,'name','')):
     class BadDigest:
      def digest(self):return bytes(32)
     return BadDigest()
    return result
   with patch.object(restore_staging.hashlib,'file_digest',side_effect=corrupt_digest):
    with self.assertRaisesRegex(ValueError,'integrity mismatch'):
     stage_verified_restore(snapshot,active,confirm=True)
   self.assertEqual(list(root.glob('storagescope-restore-*')),[])
 def test_rejects_invalid_snapshot(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);bad=root/"bad";bad.mkdir()
   with self.assertRaises(ValueError):
    stage_verified_restore(bad,root/"active",confirm=True)
if __name__=="__main__":unittest.main()
