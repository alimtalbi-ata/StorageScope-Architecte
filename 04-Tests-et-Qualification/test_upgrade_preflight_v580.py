import sqlite3
import tempfile
import unittest
from pathlib import Path
from upgrade_preflight_v580 import inspect_data_directory

class UpgradePreflightTests(unittest.TestCase):
    def test_missing_directory_is_safe_and_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'missing'
            result = inspect_data_directory(p)
            self.assertTrue(result['safe'])
            self.assertFalse(p.exists())
    def test_valid_database_is_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'campaigns.sqlite'
            with sqlite3.connect(p) as con:
                con.execute('CREATE TABLE sample (id INTEGER)')
                con.execute('PRAGMA user_version=3')
            before = p.read_bytes()
            result = inspect_data_directory(d)
            self.assertTrue(result['safe'])
            self.assertEqual(result['databases'][0]['schema_version'], 3)
            self.assertEqual(p.read_bytes(), before)
    def test_invalid_database_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'campaigns.sqlite').write_bytes(b'not a sqlite database')
            self.assertFalse(inspect_data_directory(d)['safe'])
    def test_symlink_database_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'real.sqlite').write_bytes(b'anything')
            (p / 'campaigns.sqlite').symlink_to(p / 'real.sqlite')
            self.assertFalse(inspect_data_directory(p)['safe'])
    def test_empty_directory_safe(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(inspect_data_directory(d)['safe'])
