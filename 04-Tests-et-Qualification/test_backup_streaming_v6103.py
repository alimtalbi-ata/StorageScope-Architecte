import unittest, tempfile, importlib.util, hashlib, json
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).resolve().parents[1]/'03-Sources/storagescope_windows.py'
spec=importlib.util.spec_from_file_location('ss',P);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class StreamingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.payload=b'a'*3000000
  (self.root/'campaigns.sqlite').write_bytes(self.payload)
  self.manifest={'format':'storagescope-backup-v1','files':[{'name':'campaigns.sqlite','bytes':len(self.payload),'sha256':hashlib.sha256(self.payload).hexdigest()}]}
  self.save()
 def save(self): (self.root/'manifest.json').write_text(json.dumps(self.manifest))
 def test_chunked_hash(self): self.assertEqual(mod._hash_file_streaming(self.root/'campaigns.sqlite',65536),(len(self.payload),hashlib.sha256(self.payload).hexdigest()))
 def test_valid_snapshot(self): self.assertTrue(mod.verify_backup_snapshot(self.root))
 def test_wrong_size(self): self.manifest['files'][0]['bytes']+=1;self.save();self.assertFalse(mod.verify_backup_snapshot(self.root))
 def test_boolean_size(self): self.manifest['files'][0]['bytes']=True;self.save();self.assertFalse(mod.verify_backup_snapshot(self.root))
 def test_corruption(self): (self.root/'campaigns.sqlite').write_bytes(b'b'*len(self.payload));self.assertFalse(mod.verify_backup_snapshot(self.root))
 def test_oversize_manifest(self): (self.root/'manifest.json').write_bytes(b' '* (2*1024*1024+1));self.assertFalse(mod.verify_backup_snapshot(self.root))
 def test_no_read_bytes_on_snapshot(self):
  with patch.object(Path,'read_bytes',side_effect=AssertionError('read_bytes prohibited')):
   self.assertTrue(mod.verify_backup_snapshot(self.root))
if __name__=='__main__':unittest.main()
