from contextlib import closing
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import read_audit_history
from review_registry_v622 import decide

class HistoryTests(unittest.TestCase):
 def test_missing_registry(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(FileNotFoundError): read_audit_history(Path(t)/'missing.db')
 def test_invalid_limits(self):
  for n in (0,-1,1001,True,'10'):
   with self.assertRaises(ValueError): read_audit_history('x',n)
 def test_read_only_order_and_filter(self):
  with tempfile.TemporaryDirectory() as t:
   db=Path(t)/'audit.db'
   candidates=[{'asset_ids':['a','b'],'identity_evidence':['serial']},{'asset_ids':['c','d'],'identity_evidence':['serial']}]
   from review_registry_v622 import candidate_key
   report={'reconciliation':{'candidates':candidates}}
   for c in candidates: decide(db,report,candidate_key(c),'REJECTED','tester','evidence reviewed')
   history=read_audit_history(db)
   self.assertEqual([x['seq'] for x in history],[2,1])
   self.assertEqual(len(read_audit_history(db,1)),1)
   self.assertEqual(len(read_audit_history(db,candidate=candidate_key(candidates[0]))),1)
 def test_tampered_chain_refused(self):
  import sqlite3
  with tempfile.TemporaryDirectory() as t:
   db=Path(t)/'audit.db'
   c={'asset_ids':['a','b'],'identity_evidence':[]}
   from review_registry_v622 import candidate_key
   decide(db,{'reconciliation':{'candidates':[c]}},candidate_key(c),'REJECTED','tester','reason')
   with closing(sqlite3.connect(db)) as conn:
    with conn: conn.execute("UPDATE audit SET reviewer='intruder'")
   with self.assertRaises(ValueError): read_audit_history(db)

if __name__=='__main__': unittest.main()
