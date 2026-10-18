"""Release v6.17 regression coverage."""
import unittest,ast
from pathlib import Path
from decision_guided_forms_v607 import validate_decision,validate_transition,validate_qualification,validate_committee

class GuidedAccessibilityTests(unittest.TestCase):
 def test_inline_validation_for_both_dialogs(self):
  src=Path(__file__).with_name('decision_guided_forms_v607.py').read_text()
  self.assertEqual(src.count("error.set(str(exc))"),2)
  self.assertIn("<Control-Return>",src)
  ast.parse(src)
 def test_invalid_date(self):
  with self.assertRaises(ValueError):validate_decision(dict(ident='x',subject='x',owner='x',due_date='2026-02-30',evidence_reference='x'))
 def test_transition_approval(self):
  with self.assertRaises(ValueError):validate_transition(dict(status='APPROVED',actor='x',rationale='x'))
 def test_qualification_accept_requires_all(self):
  from decision_qualification_v547 import CRITERIA
  with self.assertRaises(ValueError):validate_qualification(dict(actor='x',rationale='x',verdict='ACCEPT',criteria={x:False for x in CRITERIA}))
 def test_committee_requires_date(self):
  with self.assertRaises(ValueError):validate_committee(dict(actor='x',rationale='x',verdict='DEFER',meeting_date='bad'))
 def test_cancel_no_mutation(self):
  src=Path(__file__).with_name('decision_guided_forms_v607.py').read_text()
  self.assertGreaterEqual(src.count('result=[None]'),2)
  self.assertGreaterEqual(src.count("command=win.destroy"),2)
