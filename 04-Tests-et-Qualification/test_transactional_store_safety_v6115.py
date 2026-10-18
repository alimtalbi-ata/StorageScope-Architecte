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

    def test_connection_closes_on_success(self):
        actual = store.connect
        opened = []
        def tracked(path):
            connection = actual(path)
            opened.append(connection)
            return connection
        with patch.object(store, "connect", side_effect=tracked):
            key = store.save_snapshot(self.db, [{"id": "a"}])
            store.load_snapshot(self.db, key)
        self.assertEqual(len(opened), 2)
        for connection in opened:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")

    def test_connection_closes_on_missing_snapshot(self):
        store.save_snapshot(self.db, [])
        actual = store.connect
        opened = []
        def tracked(path):
            connection = actual(path)
            opened.append(connection)
            return connection
        with patch.object(store, "connect", side_effect=tracked):
            with self.assertRaises(KeyError):
                store.load_snapshot(self.db, "0" * 64)
        self.assertEqual(len(opened), 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute("SELECT 1")

if __name__ == "__main__":
    unittest.main()
