"""Non-destructive backup regression suite. Author: Abdelhalim Talbi."""
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "03-Sources"))
from storagescope_windows import application_paths, backup_databases

class AtomicBackupTests(unittest.TestCase):
    def test_partial_copy_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            paths=application_paths(root/"data")
            paths["views"].write_text("views", encoding="utf-8")
            destination=root/"backup"
            import storagescope_windows as app
            with patch.object(app.shutil, "copyfileobj", side_effect=OSError("simulated I/O failure")):
                with self.assertRaises(OSError):
                    backup_databases(paths, destination)
            self.assertFalse((destination/"governance-views.json").exists())
    def test_sqlite_backup_is_consistent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            paths=application_paths(root/"data")
            with sqlite3.connect(paths["decisions"]) as db:
                db.execute("CREATE TABLE t (value TEXT)")
                db.execute("INSERT INTO t VALUES ('stable')")
            files=backup_databases(paths, root/"backup")
            self.assertEqual(len(files),1)
            with sqlite3.connect(files[0]) as db:
                self.assertEqual(db.execute("SELECT value FROM t").fetchone()[0],"stable")
    def test_existing_target_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            paths=application_paths(root/"data")
            paths["views"].write_text("source", encoding="utf-8")
            dest=root/"backup"
            dest.mkdir()
            (dest/"governance-views.json").write_text("untouched", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                backup_databases(paths,dest)
            self.assertEqual((dest/"governance-views.json").read_text(encoding="utf-8"),"untouched")

if __name__=="__main__":
    unittest.main()
