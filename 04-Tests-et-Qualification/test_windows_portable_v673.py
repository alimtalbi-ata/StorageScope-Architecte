import importlib.util, pathlib, tempfile, unittest, zipfile, json, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portable_verify',ROOT/'02-Compilation-Windows'/'verify-portable-release.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PortableVerification(unittest.TestCase):
 def make(self, folder, mismatch=False):
  exe=bytearray(b'\0'*2050);exe[:2]=b'MZ';exe[0x3c:0x40]=(0x80).to_bytes(4,'little');exe[0x80:0x84]=b'PE\0\0';exe[0x84:0x86]=(0x8664).to_bytes(2,'little');exe[0x94:0x96]=(0xf0).to_bytes(2,'little');exe[0x98:0x9a]=(0x20b).to_bytes(2,'little');exe=bytes(exe)
  manifest={'version':'6.73','sha256':hashlib.sha256(exe).hexdigest(),'bytes':len(exe)}
  path=folder/'portable.zip'; mp=folder/'manifest.json';mp.write_text(json.dumps(manifest))
  with zipfile.ZipFile(path,'w') as z:
   z.writestr('StorageScope.exe',exe if not mismatch else exe+b'bad')
   z.writestr('LIRE-AVANT-UTILISATION.txt','Guide')
   z.writestr('portable-manifest-v6.73.json',json.dumps(manifest))
  return path,mp
 def test_valid(self):
  with tempfile.TemporaryDirectory() as d:
   p,m=self.make(pathlib.Path(d));self.assertEqual(module.verify(p,m,'6.73')['version'],'6.73')
 def test_tampered_binary(self):
  with tempfile.TemporaryDirectory() as d:
   p,m=self.make(pathlib.Path(d),True)
   with self.assertRaises(ValueError):module.verify(p,m,'6.73')
 def test_wrong_version(self):
  with tempfile.TemporaryDirectory() as d:
   p,m=self.make(pathlib.Path(d))
   with self.assertRaises(ValueError):module.verify(p,m,'6.72')
 def test_extra_member(self):
  with tempfile.TemporaryDirectory() as d:
   p,m=self.make(pathlib.Path(d))
   with zipfile.ZipFile(p,'a') as z:z.writestr('malicious.txt','bad')
   with self.assertRaises(ValueError):module.verify(p,m,'6.73')
 def test_build_contract(self):
  build=(ROOT/'02-Compilation-Windows'/'build-all-windows.ps1').read_text()
  engine=(ROOT/'02-Compilation-Windows'/'build-engine-windows.ps1').read_text()
  self.assertIn('verify-portable-release.py',build)
  self.assertIn('verify-portable-release.py',engine)
  self.assertIn("Filter 'qualifier-*-windows.ps1'",build)
if __name__=='__main__':unittest.main()
