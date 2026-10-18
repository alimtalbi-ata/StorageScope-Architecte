"""Legacy SQLite lifecycle regression. Author: Abdelhalim Talbi."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from governance import Governance

class Tracked(sqlite3.Connection):
    closed = 0
    def close(self):
        type(self).closed += 1
        return super().close()

class GovernanceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'governance.sqlite'
        Tracked.closed = 0

    def test_normal_context_manager(self):
        with Governance(self.path) as g:
            g.propose('D1','Test','Motif','Auteur')
            self.assertTrue(g.verify_audit())
        with self.assertRaises(sqlite3.ProgrammingError):
            g.db.execute('SELECT 1')

    def test_exception_context_manager_closes(self):
        with self.assertRaisesRegex(ValueError,'expected'):
            with Governance(self.path) as g:
                raise ValueError('expected')
        with self.assertRaises(sqlite3.ProgrammingError):
            g.db.execute('SELECT 1')

    def test_init_failure_closes_connection(self):
        original = sqlite3.connect
        def tracked(*args, **kwargs):
            kwargs['factory'] = Tracked
            return original(*args, **kwargs)
        with patch('governance.sqlite3.connect', side_effect=tracked):
            with patch.object(Tracked, 'executescript', side_effect=sqlite3.DatabaseError('schema failure')):
                with self.assertRaisesRegex(sqlite3.DatabaseError,'schema failure'):
                    Governance(self.path)
        self.assertEqual(Tracked.closed, 1)

    def test_explicit_close_still_works(self):
        g = Governance(self.path)
        g.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            g.db.execute('SELECT 1')
