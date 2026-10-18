import unittest
from decision_guided_forms_v607 import validate_committee,validate_qualification
class TestV608(unittest.TestCase):
 def test_committee_ok(self):
  self.assertEqual(validate_committee(dict(actor=' A ',meeting_date='2026-10-17',verdict='DEFER',rationale=' R '))['actor'],'A')
 def test_committee_date(self):
  with self.assertRaises(ValueError):validate_committee(dict(actor='A',meeting_date='2026-02-30',verdict='DEFER',rationale='R'))
 def test_committee_verdict(self):
  with self.assertRaises(ValueError):validate_committee(dict(actor='A',meeting_date='2026-10-17',verdict='WRONG',rationale='R'))
 def test_qualification_ok(self):
  self.assertEqual(validate_qualification(dict(actor='A',verdict='ACCEPT',rationale='R',criteria={k:True for k in ('traceability','relevance','integrity','coverage')}))['verdict'],'ACCEPT')
 def test_qualification_reject_incomplete(self):
  with self.assertRaises(ValueError):validate_qualification(dict(actor='A',verdict='ACCEPT',rationale='R',criteria={k:False for k in ('traceability','relevance','integrity','coverage')}))
 def test_qualification_missing_criteria(self):
  with self.assertRaises(ValueError):validate_qualification(dict(actor='A',verdict='REJECT',rationale='R',criteria={}))
