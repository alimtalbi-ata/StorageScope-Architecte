"""Regression tests for cumulative release ZIP integrity validation."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
import hashlib
from pathlib import Path
TOOL = Path(__file__).resolve().parents[1] / "tools" / "verify_cumulative_zip.py"
spec = importlib.util.spec_from_file_location("verify_cumulative_zip", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class ReleaseZipTests(unittest.TestCase):
    def make_zip(self, path, *, tamper=False):
        data = {name:b"6.117\n" for name in module.VERSIONS}
        data["03-Sources/test.py"] = b"print('safe')\n"
        manifest = {name:hashlib.sha256(value).hexdigest() for name,value in data.items()}
        if tamper: data["03-Sources/test.py"] = b"print('tampered')\n"
        data["07-Manifestes/SHA256-v6.117.json"] = json.dumps(manifest).encode()
        with zipfile.ZipFile(path,"w") as archive:
            for name,value in data.items(): archive.writestr(name,value)
    def test_valid_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"valid.zip";self.make_zip(p)
            self.assertTrue(module.verify(p,"6.117")["ok"])
    def test_tampered_source_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"tampered.zip";self.make_zip(p,tamper=True)
            self.assertFalse(module.verify(p,"6.117")["ok"])
    def test_version_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"valid.zip";self.make_zip(p)
            self.assertFalse(module.verify(p,"6.118")["ok"])
if __name__ == "__main__":unittest.main()
