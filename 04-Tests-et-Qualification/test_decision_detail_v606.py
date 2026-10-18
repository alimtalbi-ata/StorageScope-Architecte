import unittest
from decision_detail_v606 import decision_detail

class DetailTests(unittest.TestCase):
    def setUp(self):
        self.sheet={'id':'DEC-1','subject':'Migration SAN','status':'IN_REVIEW','priority':'P1','owner':'Ops','due_date':'2026-10-17','evidence_reference':'E-42'}
    def render(self, sheet=None, qualification=None):
        return decision_detail(self.sheet if sheet is None else sheet,{}, {}, {'status':'NON_REVUE'} if qualification is None else qualification)
    def test_summary(self):
        value=self.render(); self.assertIn('Migration SAN',value); self.assertIn('Ops',value)
    def test_no_raw_json(self):
        self.assertNotIn('"subject":',self.render())
    def test_missing_fields(self):
        self.assertIn('Non renseigné',self.render({'id':'DEC-2'}))
    def test_stale(self):
        self.assertIn('Qualification à renouveler',self.render(qualification={'stale':True}))
    def test_bad_id(self):
        with self.assertRaises(ValueError): self.render({})
    def test_bad_sections(self):
        with self.assertRaises(ValueError): decision_detail(self.sheet, None, {}, {})
