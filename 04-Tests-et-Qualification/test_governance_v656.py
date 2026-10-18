import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import format_audit_event, benchmark_filter
class TestV656(unittest.TestCase):
    def test_full_key_and_hash(self):
        e=dict(seq=1,candidate_key='key:'+'x'*200,action='REJECTED',reviewer='test',at='2026-01-01',event_hash='a'*64)
        result=format_audit_event(e)
        self.assertIn(e['candidate_key'],result)
        self.assertIn(e['event_hash'],result)
    def test_missing_fields_refused(self):
        with self.assertRaises(ValueError):format_audit_event({'seq':1})
    def test_benchmark_counts(self):
        rows=[('k1',{'asset_ids':['netapp-01']}),('k2',{'asset_ids':['pure-02']})]
        result=benchmark_filter(rows,['netapp','pure'],2)
        self.assertEqual([r['matched'] for r in result],[1,1])
    def test_benchmark_invalid_iterations(self):
        with self.assertRaises(ValueError):benchmark_filter([],[''],0)
if __name__=='__main__':unittest.main()
