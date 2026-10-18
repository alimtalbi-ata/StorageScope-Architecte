import unittest
from decision_guided_forms_v607 import validate_decision,validate_transition
class TestGuidedForms(unittest.TestCase):
 def test_decision_valid(self):
  self.assertEqual(validate_decision(dict(ident=' A ',subject='S',owner='O',due_date='2026-10-17',evidence_reference='P'))['ident'],'A')
 def test_missing(self):
  with self.assertRaises(ValueError):validate_decision({})
 def test_bad_date(self):
  with self.assertRaises(ValueError):validate_decision(dict(ident='A',subject='S',owner='O',due_date='2026-02-30',evidence_reference='P'))
 def test_transition_valid(self):
  self.assertIsNone(validate_transition(dict(status='IN_REVIEW',actor='A',rationale='R'))['approval'])
 def test_transition_approval(self):
  with self.assertRaises(ValueError):validate_transition(dict(status='APPROVED',actor='A',rationale='R'))
 def test_transition_status(self):
  with self.assertRaises(ValueError):validate_transition(dict(status='UNKNOWN',actor='A',rationale='R'))
