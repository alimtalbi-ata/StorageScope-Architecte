import unittest,tempfile,json,hashlib,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('verify_binary',ROOT/'02-Compilation-Windows/verify-binary-delivery.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name);self.names=['StorageScope.exe','StorageScope-UpgradeGate.exe','StorageScope-Setup-v6.89.exe','StorageScope-Portable-v6.89-win-x64.zip','release-manifest-v6.89.json'];self.items=[]
  for n in self.names:
   content=n.encode();(self.folder/n).write_bytes(content);self.items.append({'name':n,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)})
  self.save()
 def tearDown(self):self.tmp.cleanup()
 def save(self): (self.folder/'BINARY-MANIFEST.json').write_text(json.dumps({'version':'6.89','platform':'windows-x64','artifacts':self.items}))
 def test_valid(self):self.assertEqual(mod.validate(self.folder,'6.89'),5)
 def test_tampered(self): (self.folder/self.names[0]).write_bytes(b'tampered');self.assertRaises(ValueError,mod.validate,self.folder,'6.89')
 def test_duplicate(self):self.items[1]['name']=self.items[0]['name'];self.save();self.assertRaises(ValueError,mod.validate,self.folder,'6.89')
 def test_missing(self):(self.folder/self.names[1]).unlink();self.assertRaises(ValueError,mod.validate,self.folder,'6.89')
 def test_extra(self):(self.folder/'extra.txt').write_text('x');self.assertRaises(ValueError,mod.validate,self.folder,'6.89')
 def test_wrong_version(self):self.assertRaises(ValueError,mod.validate,self.folder,'6.88')
 def test_integrated(self):
  script=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text()
  self.assertIn("verify-binary-delivery.py') --folder $binaryStage",script)
if __name__=='__main__':unittest.main()
