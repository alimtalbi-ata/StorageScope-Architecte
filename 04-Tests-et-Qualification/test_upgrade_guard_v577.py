import sqlite3
import tempfile
import unittest
from pathlib import Path
from sqlite_upgrade_guard_v577 import inspect_database, preflight, UpgradeBlocked

class UpgradeGuardTests(unittest.TestCase):
    def test_absent(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(inspect_database(Path(d)/'missing.db')['status'], 'absent')
    def test_valid(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'a.db'
            with sqlite3.connect(path) as c:
                c.execute('CREATE TABLE a (id INTEGER)')
                c.execute('PRAGMA user_version=4')
            result = inspect_database(path)
            self.assertEqual(result['user_version'], 4)
            self.assertEqual(result['status'], 'ok')
    def test_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'bad.db'; path.write_bytes(b'not sqlite')
            with self.assertRaises(UpgradeBlocked): inspect_database(path)
    def test_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'empty.db'; path.touch()
            with self.assertRaises(UpgradeBlocked): inspect_database(path)
    def test_no_databases(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(UpgradeBlocked): preflight([Path(d)/'missing.db'])
    def test_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'a.db'
            with sqlite3.connect(path) as c: c.execute('CREATE TABLE a (id INTEGER)')
            before = path.read_bytes(); inspect_database(path)
            self.assertEqual(path.read_bytes(), before)
    def test_upgrade_script_present(self):
        script = Path(__file__).with_name('qualifier-mise-a-jour-windows.ps1').read_text()
        self.assertIn('PreviousInstaller', script)
        self.assertIn('NewInstaller', script)
        self.assertIn('source_preserved', script)
        self.assertIn('backup_verified', script)
