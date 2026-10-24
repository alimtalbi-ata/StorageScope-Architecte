import tempfile
import unittest
import sqlite3
from contextlib import closing
from pathlib import Path
from upgrade_gate_v581 import prepare_upgrade
from storagescope_windows import verify_backup_snapshot

class UpgradeGateTests(unittest.TestCase):
    def test_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            data=Path(root)/'data';data.mkdir()
            with closing(sqlite3.connect(data/'campaigns.sqlite')) as db, db:
                db.execute('create table t (id integer)');db.execute('insert into t values (7)')
            result=prepare_upgrade(data,Path(root)/'backups')
            self.assertTrue(result['safe'])
            self.assertTrue(verify_backup_snapshot(result['snapshot']))
            with closing(sqlite3.connect(data/'campaigns.sqlite')) as db, db:
                self.assertEqual(db.execute('select id from t').fetchone()[0],7)
    def test_no_data_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            data=Path(root)/'data';data.mkdir()
            with self.assertRaises(ValueError):prepare_upgrade(data,Path(root)/'backup')
    def test_nested_backup_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            data=Path(root)/'data';data.mkdir()
            with self.assertRaises(ValueError):prepare_upgrade(data,data/'backup')
    def test_corrupted_db_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            data=Path(root)/'data';data.mkdir()
            (data/'campaigns.sqlite').write_bytes(b'not a database')
            with self.assertRaises(ValueError):prepare_upgrade(data,Path(root)/'backup')
    def test_symlinked_database_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            data=Path(root)/'data';data.mkdir()
            outside=Path(root)/'outside';outside.write_bytes(b'other')
            (data/'campaigns.sqlite').symlink_to(outside)
            with self.assertRaises(ValueError):prepare_upgrade(data,Path(root)/'backup')
