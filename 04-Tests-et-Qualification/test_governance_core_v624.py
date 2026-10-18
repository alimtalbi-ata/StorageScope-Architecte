import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '03-Sources'))
from governance_core import inspect

class GovernanceCoreTests(unittest.TestCase):
    def records(self):
        return [{'id':'A','serial':'SN1','source':'one','name':'host1'}, {'id':'B','serial':'SN1','source':'two','name':'host2'}]
    def test_candidate_is_reviewable(self):
        r=inspect(self.records()); self.assertEqual(r['review_eligible'],1); self.assertEqual(len(r['reconciliation']['candidates'][0]['review_key']),64)
    def test_identity_stable_when_order_reversed(self):
        a=inspect(self.records())['reconciliation']['candidates'][0]['review_key']
        b=inspect(list(reversed(self.records())))['reconciliation']['candidates'][0]['review_key']
        self.assertEqual(a,b)
    def test_missing_id_blocks_review(self):
        records=self.records(); del records[0]['id']
        self.assertEqual(inspect(records)['review_eligible'],0)
    def test_duplicate_id_blocks_review(self):
        records=self.records(); records[1]['id']='a'
        self.assertEqual(inspect(records)['review_eligible'],0)
    def test_non_destructive(self):
        records=self.records(); import copy; before=copy.deepcopy(records)
        self.assertEqual(inspect(records)['automatic_merges'],0); self.assertEqual(records,before)
    def test_reject_non_list(self):
        with self.assertRaises(ValueError): inspect({})
if __name__=='__main__': unittest.main()
