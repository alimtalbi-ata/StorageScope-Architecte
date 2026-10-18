"""Presentation and safety regression tests. Author: Abdelhalim Talbi."""
import unittest
from decision_visual_v545 import visual_summary, evidence_navigation

class VisualTests(unittest.TestCase):
    def result(self, sheets=None):
        return {'consistency_verified':True,'production_activation':False,'audit_head':'a'*64,'decision_sheets':sheets if sheets is not None else []}
    def test_empty(self): self.assertEqual(visual_summary(self.result())['total'],0)
    def test_count(self): self.assertEqual(visual_summary(self.result([{'id':'A','priority':'P1','deadline_state':'overdue','requires_human_review':True}]))['priorities']['P1'],1)
    def test_overdue(self): self.assertEqual(visual_summary(self.result([{'id':'A','priority':'P1','deadline_state':'overdue'}]))['overdue'],1)
    def test_review(self): self.assertEqual(visual_summary(self.result([{'id':'A','priority':'P2','requires_human_review':True}]))['human_review'],1)
    def test_reject_unverified(self):
        with self.assertRaises(ValueError): visual_summary({'decision_sheets':[]})
    def test_reject_activation(self):
        r=self.result();r['production_activation']=True
        with self.assertRaises(ValueError): visual_summary(r)
    def test_reject_duplicate(self):
        with self.assertRaises(ValueError): visual_summary(self.result([{'id':'A','priority':'P1'},{'id':'A','priority':'P2'}]))
    def test_reject_priority(self):
        with self.assertRaises(ValueError): visual_summary(self.result([{'id':'A','priority':'P0'}]))
    def test_reference_not_verified(self): self.assertFalse(evidence_navigation({'id':'A','evidence_reference':'DOC-1'})['sufficiency_verified'])
    def test_missing_reference(self): self.assertEqual(evidence_navigation({'id':'A'})['reference'],'')
    def test_invalid_sheet(self):
        with self.assertRaises(ValueError): evidence_navigation({})
    def test_no_activation(self): self.assertFalse(visual_summary(self.result())['production_activation'])
