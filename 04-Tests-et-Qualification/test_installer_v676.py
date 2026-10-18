import hashlib, importlib.util, json, pathlib, struct, tempfile, unittest
from importlib.machinery import SourceFileLoader
SOURCE=pathlib.Path(__file__).resolve().parents[1]/'02-Compilation-Windows/verify-installer-release.py'
mod=SourceFileLoader('installer_validator_676',str(SOURCE)).load_module()
class InstallerPEValidation(unittest.TestCase):
    def fixture(self, machine=0x14c, magic=0x10b, sections=1, optsize=224, truncate=False):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        root=pathlib.Path(td.name); exe=root/'StorageScope-Setup-v6.76.exe'; blob=bytearray(4096)
        blob[:2]=b'MZ'; struct.pack_into('<I',blob,0x3c,128); blob[128:132]=b'PE\0\0'
        struct.pack_into('<H',blob,132,machine);struct.pack_into('<H',blob,134,sections)
        struct.pack_into('<H',blob,148,optsize);struct.pack_into('<H',blob,152,magic)
        if truncate: struct.pack_into('<H',blob,148,4000)
        exe.write_bytes(blob); manifest=root/'manifest.json'
        manifest.write_text(json.dumps({'version':'6.76','artifacts':[{'filename':exe.name,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}]}))
        return exe,manifest
    def test_valid_pe32(self):
        self.assertEqual(mod.verify_installer(*self.fixture(), '6.76')['version'],'6.76')
    def test_valid_pe64(self):
        self.assertEqual(mod.verify_installer(*self.fixture(machine=0x8664,magic=0x20b,optsize=240),'6.76')['version'],'6.76')
    def test_reject_mismatched_architecture(self):
        with self.assertRaisesRegex(ValueError,'architecture'): mod.verify_installer(*self.fixture(machine=0x8664,magic=0x10b),'6.76')
    def test_reject_zero_sections(self):
        with self.assertRaisesRegex(ValueError,'section count'): mod.verify_installer(*self.fixture(sections=0),'6.76')
    def test_reject_short_optional_header(self):
        with self.assertRaisesRegex(ValueError,'optional header'): mod.verify_installer(*self.fixture(optsize=24),'6.76')
    def test_reject_truncated_section_table(self):
        with self.assertRaisesRegex(ValueError,'optional header'): mod.verify_installer(*self.fixture(truncate=True),'6.76')
if __name__=='__main__':unittest.main()
