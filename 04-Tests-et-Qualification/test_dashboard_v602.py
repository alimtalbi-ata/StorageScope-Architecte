"""Dashboard regression tests, v6.17."""
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from windows_dashboard_v602 import dashboard_summary, metric_label

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = {k: Path(self.tmp.name)/(k+'.db') for k in ('decisions','campaigns')}

    def test_missing_databases_not_created(self):
        r=dashboard_summary(self.paths,today='2026-10-17')
        self.assertEqual(r['empty'], {'decisions':True,'campaigns':True})
        self.assertTrue(all(not p.exists() for p in self.paths.values()))

    def test_decision_counts_exclude_closed(self):
        with closing(sqlite3.connect(self.paths['decisions'])) as db, db:
            db.execute('CREATE TABLE decisions(status TEXT,due_date TEXT)')
            db.executemany('INSERT INTO decisions VALUES (?,?)', [('OPEN','2026-10-16'),('IN_REVIEW','2026-10-17'),('CLOSED','2026-10-15'),('APPROVED','2026-10-18')])
        r=dashboard_summary(self.paths,today='2026-10-17')
        self.assertEqual((r['decisions'],r['overdue'],r['due_today']),(3,1,1))

    def test_campaign_count(self):
        with closing(sqlite3.connect(self.paths['campaigns'])) as db, db:
            db.execute('CREATE TABLE campaigns(id TEXT)')
            db.executemany('INSERT INTO campaigns VALUES (?)',[('a',),('b',)])
        self.assertEqual(dashboard_summary(self.paths)['campaigns'],2)

    def test_corrupt_database_reports_error(self):
        self.paths['decisions'].write_bytes(b'not a sqlite database')
        r=dashboard_summary(self.paths)
        self.assertIn('decisions',r['errors'])
        self.assertIsNone(r['decisions'])

    def test_metric_labels(self):
        self.assertEqual(metric_label(0),'0')
        self.assertEqual(metric_label(None,missing=True),'À initialiser')
        self.assertIn('Erreur',metric_label(None,error=True))
