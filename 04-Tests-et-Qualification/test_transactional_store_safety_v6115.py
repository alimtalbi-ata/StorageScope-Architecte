"""v6.115 transactional snapshot regression tests."""
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "03-Sources"))
import transactional_store as store

class SnapshotSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = pathlib.Path(self.temp.name) / "assets.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_database_read_does_not_create_files(self):
        with self.assertRaises(KeyError):
            store.load_snapshot(self.db, "0" * 64)
        self.assertFalse(self.db.exists())

    def test_read_does_not_migrate_schema(self):
        connection = sqlite3.connect(self.db)
        connection.execute("PRAGMA user_version=0")
        connection.commit()
        connection.close()
        with self.assertRaises(sqlite3.OperationalError):
            store.load_snapshot(self.db, "0" * 64)
        with sqlite3.connect(self.db) as check:
            self.assertEqual(check.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(check.execute("SELECT count(*) FROM sqlite_master WHERE name='snapshots'").fetchone()[0], 0)

    def test_trimmed_identifier_roundtrip(self):
        key = store.save_snapshot(self.db, [{"id": " b "}, {"id": "a"}])
        self.assertEqual(store.load_snapshot(self.db, key), [{"id": "a"}, {"id": "b"}])

    def test_duplicate_after_normalization_rejected(self):
        with self.assertRaises(ValueError):
            store.save_snapshot(self.db, [{"id": "a"}, {"id": " a "}])
        self.assertFalse(self.db.exists())

    def test_unchanged_caller_data(self):
        assets = [{"id": " a "}]
        store.save_snapshot(self.db, assets)
        self.assertEqual(assets, [{"id": " a "}])

    def test_write_connection_closes_on_success(self):
        actual = store.connect
        opened = []
        def tracked(path):
            connection = actual(path)
            opened.append(connection)
            return connection
        with patch.object(store, "connect", side_effect=tracked):
            key = store.save_snapshot(self.db, [{"id": "a"}])
        self.assertEqual(len(opened), 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute("SELECT 1")
        self.assertEqual(store.load_snapshot(self.db, key), [{"id": "a"}])

    def test_read_connection_closes_on_success_and_error(self):
        store.save_snapshot(self.db, [{"id": "a"}])
        actual = store.sqlite3.connect
        opened = []
        def tracked(*args, **kwargs):
            connection = actual(*args, **kwargs)
            opened.append(connection)
            return connection
        with patch.object(store.sqlite3, "connect", side_effect=tracked):
            key = store.save_snapshot(self.db, [{"id": "a"}])
            store.load_snapshot(self.db, key)
            with self.assertRaises(KeyError):
                store.load_snapshot(self.db, "0" * 64)
        # The write and both read connections must be closed.
        self.assertEqual(len(opened), 3)
        for connection in opened:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")

if __name__ == "__main__":
    unittest.main()
