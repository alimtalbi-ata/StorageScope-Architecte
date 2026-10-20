"""Regression: existing backups must never be overwritten. Author: Abdelhalim Talbi."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from storagescope_windows import application_paths, backup_databases

class BackupSafetyTests(unittest.TestCase):
    def test_existing_target_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=application_paths(root/'data');paths['views'].write_text('original')
            dest=root/'backup';dest.mkdir();target=dest/paths['views'].name;target.write_text('do not overwrite')
            with self.assertRaises(FileExistsError):backup_databases(paths,dest)
            self.assertEqual(target.read_text(),'do not overwrite')
    def test_nested_destination_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=application_paths(root/'data')
            with self.assertRaises(ValueError):backup_databases(paths,root/'data'/'nested')
            self.assertFalse((root/'data'/'nested').exists())
    def test_normal_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=application_paths(root/'data');paths['views'].write_text('valid')
            files=backup_databases(paths,root/'backup')
            self.assertEqual(len(files),1)
            self.assertEqual(files[0].read_text(),'valid')
if __name__=='__main__':unittest.main()
