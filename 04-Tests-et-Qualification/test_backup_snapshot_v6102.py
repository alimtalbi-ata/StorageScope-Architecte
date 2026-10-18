import importlib.util, unittest, tempfile, json, hashlib
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'03-Sources/storagescope_windows.py'
spec=importlib.util.spec_from_file_location('storagescope_windows_v6102',P)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class SnapshotSecurity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.data=b'snapshot-content'
        (self.folder/'campaigns.sqlite').write_bytes(self.data)
        self.manifest={'format':'storagescope-backup-v1','files':[{'name':'campaigns.sqlite','bytes':len(self.data),'sha256':hashlib.sha256(self.data).hexdigest()}]}
        self.save()
    def save(self):
        (self.folder/'manifest.json').write_text(json.dumps(self.manifest))
    def test_valid_snapshot(self):self.assertTrue(mod.verify_backup_snapshot(self.folder))
    def test_hash_mismatch(self):
        (self.folder/'campaigns.sqlite').write_bytes(b'changed');self.assertFalse(mod.verify_backup_snapshot(self.folder))
    def test_path_traversal(self):
        self.manifest['files'][0]['name']='../campaigns.sqlite';self.save();self.assertFalse(mod.verify_backup_snapshot(self.folder))
    def test_windows_path_separator(self):
        self.manifest['files'][0]['name']=r'..\campaigns.sqlite';self.save();self.assertFalse(mod.verify_backup_snapshot(self.folder))
    def test_symlink_is_rejected(self):
        target=self.folder/'campaigns.sqlite';target.rename(self.folder/'actual.bin')
        try:target.symlink_to(self.folder/'actual.bin')
        except (OSError,NotImplementedError):self.skipTest('symlinks unavailable')
        self.assertFalse(mod.verify_backup_snapshot(self.folder))
    def test_nested_entry_rejected(self):
        (self.folder/'unexpected').mkdir();self.assertFalse(mod.verify_backup_snapshot(self.folder))
    def test_duplicate_manifest_entries(self):
        self.manifest['files'].append(dict(self.manifest['files'][0]));self.save();self.assertFalse(mod.verify_backup_snapshot(self.folder))
if __name__=='__main__':unittest.main()
