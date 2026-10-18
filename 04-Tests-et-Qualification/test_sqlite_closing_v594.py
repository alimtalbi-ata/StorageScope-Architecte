"""Regression tests for explicit SQLite resource closure. Author: Abdelhalim Talbi."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import storagescope_windows as app
from upgrade_preflight_v580 import inspect_data_directory

class TrackedConnection(sqlite3.Connection):
    closed_count = 0
    def close(self):
        type(self).closed_count += 1
        return super().close()

class SQLiteClosingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        TrackedConnection.closed_count = 0

    def _track(self, module):
        original = sqlite3.connect
        def connect(*args, **kwargs):
            kwargs['factory'] = TrackedConnection
            return original(*args, **kwargs)
        return patch.object(module.sqlite3, 'connect', side_effect=connect)

    def test_health_success_closes_connection(self):
        db = self.root / 'test.sqlite'
        with sqlite3.connect(db) as con: con.execute('CREATE TABLE t(x)')
        with self._track(app): self.assertEqual(app.database_health(db), 'OK')
        self.assertEqual(TrackedConnection.closed_count, 1)

    def test_health_failure_closes_connection(self):
        db = self.root / 'test.sqlite'
        db.write_bytes(b'not a database')
        with self._track(app):
            with self.assertRaises(sqlite3.DatabaseError): app.database_health(db)
        self.assertEqual(TrackedConnection.closed_count, 1)

    def test_backup_closes_source_and_destination(self):
        paths = app.application_paths(self.root / 'data')
        with sqlite3.connect(paths['decisions']) as con: con.execute('CREATE TABLE t(x)')
        with self._track(app):
            files = app.backup_databases(paths, self.root / 'backup')
        self.assertEqual(len(files), 1)
        self.assertEqual(TrackedConnection.closed_count, 2)

    def test_preflight_closes_readonly_connection(self):
        data = self.root / 'data'; data.mkdir()
        with sqlite3.connect(data / 'campaigns.sqlite') as con: con.execute('CREATE TABLE t(x)')
        import upgrade_preflight_v580 as preflight
        with self._track(preflight): self.assertTrue(inspect_data_directory(data)['safe'])
        self.assertEqual(TrackedConnection.closed_count, 1)

    def test_missing_health_does_not_open_database(self):
        with self._track(app): self.assertEqual(app.database_health(self.root / 'missing.sqlite'), 'ABSENTE')
        self.assertEqual(TrackedConnection.closed_count, 0)
