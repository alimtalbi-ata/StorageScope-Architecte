"""Snapshot isolation and indexed governance checks. Author: Abdelhalim Talbi."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from decision_governance_v537 import GovernanceStore
from decision_integrity_v540 import consistency_report

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=GovernanceStore(Path(tmp.name)/'review.sqlite')
        self.store.create('ADR-1','Architecture SAN','Architect','2026-10-01','proof')

    def test_single_report_connection(self):
        original=self.store._connect
        calls=[]
        def tracked():
            calls.append(1)
            return original()
        with patch.object(self.store,'_connect',side_effect=tracked):
            self.store.governance_report(today='2026-10-16')
        self.assertEqual(len(calls),1)

    def test_consistency_does_not_read_audit_twice(self):
        with patch.object(self.store,'report',side_effect=AssertionError('redundant read')):
            self.assertTrue(consistency_report(self.store,today='2026-10-16')['consistent'])

    def test_report_contains_verified_audit(self):
        r=self.store.governance_report(today='2026-10-16')
        self.assertEqual(r['audit'][0]['event']['event'],'CREATED')
        self.assertEqual(r['audit_head'],r['audit'][-1]['entry_hash'])

    def test_corrupt_audit_fails_closed(self):
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE decision_audit SET payload='{}' WHERE seq=1")
        with self.assertRaises(ValueError):self.store.governance_report()

    def test_counts_and_followups(self):
        self.store.followup('ADR-1','Architect','Reminder',today='2026-10-16')
        r=self.store.governance_report(today='2026-10-16')
        self.assertTrue(r['decisions'][0]['followup_recorded'])
        self.assertEqual(r['kpis']['followups_recorded'],1)

    def test_empty_store(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        r=GovernanceStore(Path(tmp.name)/'empty.db').governance_report()
        self.assertEqual(r['audit'],[])
        self.assertEqual(r['kpis']['open'],0)

    def test_integrity_link(self):
        e={'earlier_id':'A','later_id':'B','code':'route_mismatch','evidence_ids':['P'],
           'earlier_sha256':'a'*64,'later_sha256':'b'*64}
        self.store.link_event('ADR-1',e,evidence_id='P')
        self.assertTrue(consistency_report(self.store)['consistent'])

    def test_report_is_consultative(self):
        r=self.store.governance_report()
        self.assertFalse(r['production_activation'])
        self.assertTrue(r['recommendation_only'])

if __name__=='__main__':unittest.main()
