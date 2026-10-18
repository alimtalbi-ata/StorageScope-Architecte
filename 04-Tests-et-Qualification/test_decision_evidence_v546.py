"""Evidence completeness regression tests. Author: Abdelhalim Talbi."""
import unittest
from decision_evidence_v546 import assess_evidence, evidence_overview

class EvidenceTests(unittest.TestCase):
    def test_missing_both(self): self.assertEqual(len(assess_evidence({'id':'A'})['completeness_flags']),2)
    def test_missing_reference(self): self.assertIn('reference_missing',assess_evidence({'id':'A','links':[{'evidence_id':'X','earlier_sha256':'a','later_sha256':'b'}]})['completeness_flags'])
    def test_missing_link(self): self.assertIn('linked_alert_missing',assess_evidence({'id':'A','evidence_reference':'DOC'})['completeness_flags'])
    def test_complete_not_qualified(self):
        a=assess_evidence({'id':'A','evidence_reference':'DOC','links':[{'evidence_id':'X','earlier_sha256':'a','later_sha256':'b'}]})
        self.assertEqual(a['state'],'unqualified');self.assertFalse(a['evidence_sufficiency_verified'])
    def test_missing_link_id(self): self.assertIn('link_evidence_id_missing',assess_evidence({'id':'A','links':[{}]})['completeness_flags'])
    def test_missing_hash(self): self.assertIn('link_hash_missing',assess_evidence({'id':'A','links':[{}]})['completeness_flags'])
    def test_no_activation(self): self.assertFalse(assess_evidence({'id':'A'})['production_activation'])
    def test_bad_id(self):
        with self.assertRaises(ValueError): assess_evidence({'id':' '})
    def test_bad_links(self):
        with self.assertRaises(ValueError): assess_evidence({'id':'A','links':'oops'})
    def test_bad_link_item(self):
        with self.assertRaises(ValueError): assess_evidence({'id':'A','links':[1]})
    def test_empty_overview(self): self.assertEqual(evidence_overview([])['total'],0)
    def test_overview_counts(self): self.assertEqual(evidence_overview([{'id':'A'},{'id':'B','evidence_reference':'DOC','links':[{'evidence_id':'X','earlier_sha256':'a','later_sha256':'b'}]}])['incomplete'],1)
    def test_duplicate(self):
        with self.assertRaises(ValueError): evidence_overview([{'id':'A'},{'id':'A'}])
    def test_never_qualified(self): self.assertEqual(evidence_overview([{'id':'A'}])['qualified'],0)
