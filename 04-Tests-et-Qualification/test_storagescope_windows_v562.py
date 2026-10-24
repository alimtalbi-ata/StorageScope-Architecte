"""Windows shell regression tests. Author: Abdelhalim Talbi."""
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from storagescope_windows import application_paths, database_health, backup_databases, VERSION

class TestWindowsShell562(unittest.TestCase):
    def test_version(self): self.assertRegex(VERSION, r'^[56]\.[0-9]+$')
    def test_missing_db_does_not_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'missing.db'
            self.assertEqual(database_health(db), 'ABSENTE')
            self.assertFalse(db.exists())
    def test_backup_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = application_paths(Path(tmp)/'active')
            with closing(sqlite3.connect(paths['decisions'])) as db, db:
                db.execute('CREATE TABLE t(x INTEGER)')
                db.execute('INSERT INTO t VALUES(42)')
            output = backup_databases(paths, Path(tmp)/'backup')
            self.assertEqual(len(output), 1)
            self.assertEqual(database_health(output[0]), 'OK')
            with closing(sqlite3.connect(output[0])) as db, db:
                self.assertEqual(db.execute('SELECT x FROM t').fetchone()[0],42)
    def test_reject_same_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = application_paths(tmp)
            with self.assertRaises(ValueError): backup_databases(paths, tmp)
    def test_views_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = application_paths(Path(tmp)/'active')
            paths['views'].write_text('{}')
            output = backup_databases(paths, Path(tmp)/'backup')
            self.assertEqual(len(output),1)
            self.assertEqual(output[0].read_text(),'{}')
