import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from decision_governance_v537 import GovernanceStore

class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'db.sqlite';self.db=GovernanceStore(self.path)
        self.db.create('ADR-1','SAN','Architect','2026-10-10','sha256:abc')
        self.event={'earlier_id':'C1','later_id':'C2','code':'regression',
                    'evidence_ids':['m1'],'earlier_sha256':'a'*64,'later_sha256':'b'*64}
    def test_overdue(self):self.assertEqual(self.db.governance_report(today='2026-10-16')['kpis']['overdue'],1)
    def test_upcoming(self):self.assertEqual(self.db.governance_report(today='2026-10-01')['decisions'][0]['deadline_state'],'upcoming')
    def test_due_today(self):self.assertEqual(self.db.governance_report(today='2026-10-10')['kpis']['due_today'],1)
    def test_link_and_idempotence(self):
        self.assertTrue(self.db.link_event('ADR-1',self.event,evidence_id='m1'))
        self.assertFalse(self.db.link_event('ADR-1',self.event,evidence_id='m1'))
        self.assertEqual(self.db.governance_report()['kpis']['unlinked'],0)
    def test_reject_fabricated_evidence(self):
        with self.assertRaises(ValueError):self.db.link_event('ADR-1',self.event,evidence_id='fake')
    def test_reject_bad_hash(self):
        event=dict(self.event,later_sha256='bogus')
        with self.assertRaises(ValueError):self.db.link_event('ADR-1',event)
    def test_followup_once(self):
        self.assertTrue(self.db.followup('ADR-1','Human','Reminder',today='2026-10-16'))
        self.assertFalse(self.db.followup('ADR-1','Human','Reminder',today='2026-10-16'))
        self.assertEqual(self.db.governance_report()['kpis']['followups_recorded'],1)
    def test_no_early_followup(self):
        with self.assertRaises(ValueError):self.db.followup('ADR-1','Human','Reminder',today='2026-10-01')
    def test_export(self):
        target=Path(self.temp.name)/'report.json'
        self.db.export_governance(target,today='2026-10-16')
        self.assertEqual(json.loads(target.read_text())['kpis']['overdue'],1)
    def test_audit_tamper_detected(self):
        with sqlite3.connect(self.path) as db:db.execute("UPDATE decision_audit SET payload='{}' WHERE seq=1")
        with self.assertRaises(ValueError):self.db.governance_report()
    def test_no_production_activation(self):self.assertFalse(self.db.governance_report()['production_activation'])
