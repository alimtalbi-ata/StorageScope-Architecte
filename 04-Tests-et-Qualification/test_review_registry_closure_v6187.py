"""SQLite handle regression: approval and rejected duplicates must close the DB.

Author: Abdelhalim Talbi. Uses a real temporary SQLite database, not a mock DB.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / '03-Sources' / 'review_registry_v621.py'
spec = importlib.util.spec_from_file_location('review_registry_v621_v6187', SOURCE)
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)

CANDIDATE = {'indices':[0,1], 'identity_evidence':['serial'],
             'sources':['vendor-a','vendor-b'], 'conflicts':[]}
REPORT = {'reconciliation': {'candidates':[CANDIDATE]}}

class TrackedConnection(sqlite3.Connection):
    close_count = 0
    def close(self):
        type(self).close_count += 1
        return super().close()


class ReviewRegistryConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'review.sqlite'
        TrackedConnection.close_count = 0

    def _track_connect(self):
        original = sqlite3.connect
        def connect(*args, **kwargs):
            kwargs['factory'] = TrackedConnection
            return original(*args, **kwargs)
        return patch.object(registry.sqlite3, 'connect', side_effect=connect)

    def test_success_closes_connection_and_commits_audit(self):
        with self._track_connect():
            result = registry.decide(self.db, REPORT, registry.candidate_key(CANDIDATE),
                                     'APPROVED', 'architect', 'verified evidence')
        self.assertFalse(result['inventory_changed'])
        self.assertEqual(TrackedConnection.close_count, 1)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM events').fetchone()[0], 1)
        conn.close()

    def test_duplicate_refusal_closes_connection_and_preserves_decision(self):
        key = registry.candidate_key(CANDIDATE)
        with self._track_connect():
            registry.decide(self.db, REPORT, key, 'REJECTED', 'architect', 'different asset')
            with self.assertRaisesRegex(ValueError, 'immutable'):
                registry.decide(self.db, REPORT, key, 'APPROVED', 'architect', 'retry')
        self.assertEqual(TrackedConnection.close_count, 2)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT status FROM decisions').fetchone()[0], 'REJECTED')
        conn.close()

if __name__ == '__main__':
    unittest.main()
