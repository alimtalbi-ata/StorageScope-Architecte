import sqlite3
import tempfile
import unittest
import warnings
from pathlib import Path
from campaign_history_v526 import CampaignHistory
from architecture_decisions_v536 import ClosingConnection

class CampaignSqliteResourceTests(unittest.TestCase):
    def test_connection_is_closed_after_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=CampaignHistory(Path(tmp)/"campaigns.sqlite")
            with store._connect() as db:
                self.assertEqual(db.execute("SELECT 1").fetchone()[0],1)
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute("SELECT 1")
    def test_failed_transaction_rolls_back_and_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=CampaignHistory(Path(tmp)/"campaigns.sqlite")
            with self.assertRaises(RuntimeError):
                with store._connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("CREATE TABLE temp_rollback (value TEXT)")
                    raise RuntimeError("abort")
            with store._connect() as db:
                self.assertFalse(db.execute("SELECT name FROM sqlite_master WHERE name='temp_rollback'").fetchone())
    def test_connection_factory_is_closing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=CampaignHistory(Path(tmp)/"campaigns.sqlite")
            with store._connect() as db:
                self.assertIsInstance(db, ClosingConnection)
    def test_no_resource_warning_for_campaign_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=CampaignHistory(Path(tmp)/"campaigns.sqlite")
            with warnings.catch_warnings(record=True) as found:
                warnings.simplefilter("always", ResourceWarning)
                for _ in range(4): store.list()
            self.assertFalse([w for w in found if issubclass(w.category, ResourceWarning)])
    def test_immediate_transaction_before_id_lookup(self):
        import inspect
        body=inspect.getsource(CampaignHistory.add)
        self.assertLess(body.index("BEGIN IMMEDIATE"),body.index("SELECT digest"))
