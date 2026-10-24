"""StorageScope v6.12 SQLite lifecycle regression tests. Author: Abdelhalim Talbi."""
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from governance import Governance

class GovernanceSQLiteLifecycleV612(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'governance.sqlite'

    def test_close_twice_is_safe(self):
        reg = Governance(self.path)
        reg.close()
        reg.close()
        self.assertTrue(reg._closed)

    def test_context_exception_closes_handle(self):
        reg = Governance(self.path)
        with self.assertRaisesRegex(RuntimeError, 'stop'):
            with reg:
                raise RuntimeError('stop')
        self.assertTrue(reg._closed)

    def test_close_rolls_back_pending_transaction(self):
        reg = Governance(self.path)
        reg.db.execute('BEGIN IMMEDIATE')
        reg.db.execute("INSERT INTO decisions(id,title,rationale,author,created_at) VALUES('X','T','R','A','now')")
        reg.close()
        with closing(sqlite3.connect(self.path)) as con, con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM decisions').fetchone()[0], 0)

    def test_reopen_after_close(self):
        reg = Governance(self.path)
        reg.close()
        with Governance(self.path) as fresh:
            self.assertTrue(fresh.verify_audit())
