"""Committee digest regression tests. Author: Abdelhalim Talbi."""
import json
import tempfile
import unittest
from pathlib import Path
from decision_qualification_v547 import QualificationStore
from decision_committee_evidence_v555 import committee_evidence_digest,export_committee_evidence

class CommitteeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name)
        self.store=QualificationStore(str(self.dir/'db.sqlite'))
        self.store.create('D1','subject','owner','2026-12-01','REF-1')
    def qualify(self):
        self.store.qualify('D1','reviewer','ACCEPT',dict.fromkeys(('traceability','relevance','integrity','coverage'),True),'checked')
    def test_unreviewed(self):
        self.assertEqual(committee_evidence_digest(self.store,'D1')['current_state'],'UNREVIEWED')
    def test_reference(self):
        self.assertEqual(committee_evidence_digest(self.store,'D1')['evidence_references'],['REF-1'])
    def test_anchor(self):
        self.assertEqual(len(committee_evidence_digest(self.store,'D1')['audit_head']),64)
    def test_current(self):
        self.qualify(); self.assertEqual(committee_evidence_digest(self.store,'D1')['current_state'],'CURRENT')
    def test_review(self):
        self.qualify(); self.assertEqual(committee_evidence_digest(self.store,'D1')['latest_review']['verdict'],'ACCEPT')
    def test_md(self):
        p=self.dir/'committee.md';export_committee_evidence(self.store,'D1',p)
        self.assertIn('REF-1',p.read_text())
    def test_json(self):
        p=self.dir/'committee.json';export_committee_evidence(self.store,'D1',p,format='json')
        self.assertEqual(json.loads(p.read_text())['decision_id'],'D1')
    def test_bad_format(self):
        with self.assertRaises(ValueError):export_committee_evidence(self.store,'D1',self.dir/'out',format='csv')
    def test_unknown(self):
        with self.assertRaises(KeyError):committee_evidence_digest(self.store,'MISSING')
    def test_never_activate(self):
        self.assertFalse(committee_evidence_digest(self.store,'D1')['production_activation'])
    def test_no_sufficiency_claim(self):
        self.assertFalse(committee_evidence_digest(self.store,'D1')['evidence_sufficiency_verified'])
