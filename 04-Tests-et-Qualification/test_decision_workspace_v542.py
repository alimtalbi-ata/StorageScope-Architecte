import unittest
from unittest.mock import patch
from decision_workspace_v542 import workspace

BASE={'filters':{'owner':None,'status':'all','deadline':'all'},'global_kpis':{'overdue':1},'audit_head':'abc',
      'decision_sheets':[{'id':'ADR-2','subject':'SAN zoning','owner':'Alice','status':'IN_REVIEW','evidence_reference':'EV-2','rationale':'analyse','priority':'P2','due_date':'2026-12-01','requires_human_review':True},
                         {'id':'ADR-1','subject':'NAS migration','owner':'Bob','status':'OPEN','evidence_reference':'EV-1','rationale':'plan','priority':'P1','due_date':'2026-11-01','requires_human_review':True}]}
class WorkspaceTests(unittest.TestCase):
    def test_all(self):
        with patch('decision_workspace_v542.verified_review',return_value=BASE):
            r=workspace(None);self.assertEqual(r['visible_kpis']['count'],2)
    def test_search_subject(self):
        with patch('decision_workspace_v542.verified_review',return_value=BASE):
            self.assertEqual(workspace(None,query='nas')['decision_sheets'][0]['id'],'ADR-1')
    def test_search_owner(self):
        with patch('decision_workspace_v542.verified_review',return_value=BASE):
            self.assertEqual(workspace(None,query='alice')['visible_kpis']['count'],1)
    def test_search_evidence(self):
        with patch('decision_workspace_v542.verified_review',return_value=BASE):
            self.assertEqual(workspace(None,query='ev-2')['visible_kpis']['count'],1)
    def test_casefold(self):
        with patch('decision_workspace_v542.verified_review',return_value=BASE):
            self.assertEqual(workspace(None,query='SAN')['visible_kpis']['count'],1)
    def test_priority_sort(self):
        with patch('decision_workspace_v542.verified_review',return_value=BASE):
            self.assertEqual(workspace(None)['decision_sheets'][0]['priority'],'P1')
    def test_empty(self):
        with patch('decision_workspace_v542.verified_review',return_value=BASE):
            self.assertEqual(workspace(None,query='missing')['visible_kpis']['count'],0)
    def test_bad_query(self):
        with self.assertRaises(ValueError):workspace(None,query=12)
    def test_too_long(self):
        with self.assertRaises(ValueError):workspace(None,query='a'*257)
    def test_fail_closed(self):
        with patch('decision_workspace_v542.verified_review',side_effect=ValueError('corrupt')):
            with self.assertRaises(ValueError):workspace(None)
    def test_no_activation(self):
        with patch('decision_workspace_v542.verified_review',return_value=BASE):
            self.assertFalse(workspace(None)['production_activation'])
if __name__=='__main__':unittest.main()
