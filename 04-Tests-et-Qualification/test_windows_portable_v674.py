import unittest, tempfile, pathlib, zipfile, json, hashlib, importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portable_verifier_674', ROOT/'02-Compilation-Windows'/'verify-portable-release.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def fixture(machine=0x8664, magic=0x20b, signature=b'PE\0\0'):
    exe=bytearray(4096);exe[:2]=b'MZ';exe[0x3c:0x40]=(0x80).to_bytes(4,'little')
    exe[0x80:0x84]=signature;exe[0x84:0x86]=machine.to_bytes(2,'little')
    exe[0x94:0x96]=(0xf0).to_bytes(2,'little');exe[0x98:0x9a]=magic.to_bytes(2,'little')
    return bytes(exe)
class PortablePEContract(unittest.TestCase):
    def check(self, binary, accepted):
        with tempfile.TemporaryDirectory() as tmp:
            folder=pathlib.Path(tmp); manifest={'version':'6.74','sha256':hashlib.sha256(binary).hexdigest(),'bytes':len(binary)}
            (folder/'manifest.json').write_text(json.dumps(manifest))
            with zipfile.ZipFile(folder/'release.zip','w') as z:
                z.writestr('StorageScope.exe',binary)
                z.writestr('LIRE-AVANT-UTILISATION.txt','Guide')
                z.writestr('portable-manifest-v6.74.json',json.dumps(manifest))
            if accepted:self.assertEqual(mod.verify(folder/'release.zip',folder/'manifest.json','6.74')['version'],'6.74')
            else:
                with self.assertRaises(ValueError):mod.verify(folder/'release.zip',folder/'manifest.json','6.74')
    def test_valid_amd64_pe32plus(self):self.check(fixture(),True)
    def test_wrong_architecture_i386(self):self.check(fixture(machine=0x14c),False)
    def test_wrong_pe_format(self):self.check(fixture(magic=0x10b),False)
    def test_invalid_pe_signature(self):self.check(fixture(signature=b'FAKE'),False)
    def test_non_executable_payload(self):self.check(b'MZ'+b'X'*4094,False)
if __name__=='__main__':unittest.main()
