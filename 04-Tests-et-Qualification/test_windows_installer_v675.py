import hashlib, importlib.util, json, pathlib, struct, tempfile, unittest

p=pathlib.Path(__file__).resolve().parents[1]/'02-Compilation-Windows'/'verify-installer-release.py'
spec=importlib.util.spec_from_file_location('verify_installer_release',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class InstallerReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); d=pathlib.Path(self.tmp.name)
        self.exe=d/'StorageScope-Setup-v6.75.exe'; self.man=d/'manifest.json'
        payload=bytearray(2048);payload[:2]=b'MZ';struct.pack_into('<I',payload,0x3c,128);payload[128:132]=b'PE\x00\x00';struct.pack_into('<H',payload,132,0x14c);struct.pack_into('<H',payload,148,224);struct.pack_into('<H',payload,152,0x10b)
        self.exe.write_bytes(payload); self.record={'version':'6.75','artifacts':[{'filename':self.exe.name,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}]};self.save()
    def save(self): self.man.write_text(json.dumps(self.record))
    def check(self): return m.verify_installer(self.exe,self.man,'6.75')
    def test_valid_structural_fixture(self): self.assertEqual(self.check()['version'],'6.75')
    def test_modified_executable(self):
        with self.exe.open('ab') as f:f.write(b'tampered')
        with self.assertRaisesRegex(ValueError,'size mismatch'):self.check()
    def test_wrong_manifest_version(self):
        self.record['version']='6.74';self.save()
        with self.assertRaisesRegex(ValueError,'version mismatch'):self.check()
    def test_duplicate_manifest_entry(self):
        self.record['artifacts'].append(dict(self.record['artifacts'][0]));self.save()
        with self.assertRaisesRegex(ValueError,'exactly once'):self.check()
    def test_fake_pe(self):
        self.exe.write_bytes(b'X'*2048);self.record['artifacts'][0]['sha256']=hashlib.sha256(self.exe.read_bytes()).hexdigest();self.save()
        with self.assertRaisesRegex(ValueError,'MZ'):self.check()
    def test_missing_installer(self):
        self.exe.unlink()
        with self.assertRaisesRegex(ValueError,'Missing'):self.check()

if __name__=='__main__': unittest.main()
