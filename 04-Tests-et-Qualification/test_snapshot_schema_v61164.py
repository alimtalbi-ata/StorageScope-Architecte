"""Snapshot manifest schema regression. Author: Abdelhalim Talbi."""
import unittest,tempfile,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from storagescope_windows import verify_backup_snapshot
class SnapshotSchemaTests(unittest.TestCase):
 def check(self, entries, expected):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=b'{}';(root/'governance-views.json').write_bytes(data)
   (root/'manifest.json').write_text(json.dumps({'format':'storagescope-backup-v1','files':entries}),encoding='utf-8')
   self.assertEqual(verify_backup_snapshot(root),expected)
 def valid(self):
  return {'name':'governance-views.json','bytes':2,'sha256':hashlib.sha256(b'{}').hexdigest()}
 def test_valid(self):self.check([self.valid()],True)
 def test_invalid_list(self):self.check({'name':'governance-views.json'},False)
 def test_invalid_entry(self):self.check(['invalid'],False)
 def test_unknown_file(self):
  e=self.valid();e['name']='arbitrary.json';self.check([e],False)
 def test_invalid_digest(self):
  e=self.valid();e['sha256']='not-a-digest';self.check([e],False)
if __name__=='__main__':unittest.main()
