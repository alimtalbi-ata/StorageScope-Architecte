"""SQLite lifecycle regression tests v6.13. Author: Abdelhalim Talbi."""
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from architecture_decisions_v536 import DecisionStore, ClosingConnection
from campaign_history_v526 import CampaignHistory
from windows_dashboard_v602 import _read_existing

class TestLifecycle613(unittest.TestCase):
    def test_decision_connect_pragma_failure_closes(self):
        with tempfile.TemporaryDirectory() as td:
            store = DecisionStore(Path(td)/'decisions.sqlite')
            self._assert_pragma_failure_closes('architecture_decisions_v536.sqlite3.connect', store._connect)

    def test_campaign_connect_pragma_failure_closes(self):
        with tempfile.TemporaryDirectory() as td:
            store = CampaignHistory(Path(td)/'campaigns.sqlite')
            self._assert_pragma_failure_closes('campaign_history_v526.sqlite3.connect', store._connect)

    def _assert_pragma_failure_closes(self, target, method):
        class Faulty(ClosingConnection):
            def execute(self, sql, *args, **kwargs):
                if sql.startswith('PRAGMA busy_timeout'): raise sqlite3.OperationalError('simulated PRAGMA failure')
                return super().execute(sql, *args, **kwargs)
        created=[]
        original=sqlite3.connect
        def wrapped(*args, **kwargs):
            kwargs['factory']=Faulty
            db=original(*args, **kwargs)
            created.append(db)
            return db
        with patch(target, side_effect=wrapped):
            with self.assertRaisesRegex(sqlite3.OperationalError,'simulated'):
                method()
        self.assertEqual(len(created),1)
        with self.assertRaises(sqlite3.ProgrammingError): created[0].execute('SELECT 1')

    def test_dashboard_read_closes_connection(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'db.sqlite'
            with closing(sqlite3.connect(path)) as db, db: db.execute('CREATE TABLE t (v INTEGER)')
            created=[]
            original=sqlite3.connect
            def wrapped(*args, **kwargs):
                db=original(*args, **kwargs)
                created.append(db)
                return db
            with patch('windows_dashboard_v602.sqlite3.connect',side_effect=wrapped):
                self.assertEqual(_read_existing(path,'SELECT count(*) FROM t'),[(0,)])
            self.assertEqual(len(created),1)
            with self.assertRaises(sqlite3.ProgrammingError): created[0].execute('SELECT 1')

    def test_dashboard_missing_db_does_not_create(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'missing.sqlite'
            self.assertIsNone(_read_existing(path,'SELECT 1'))
            self.assertFalse(path.exists())

if __name__=='__main__': unittest.main()
