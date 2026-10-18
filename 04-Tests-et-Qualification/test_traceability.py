import tempfile, unittest
from pathlib import Path
from governance import Governance
from traceability import Traceability
class TraceabilityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.g=Governance(Path(self.tmp.name)/'test.db'); self.t=Traceability(self.g)
  self.g.propose('D1','Design','Reason','author')
 def tearDown(self): self.g.close(); self.tmp.cleanup()
 def test_missing_evidence_blocks(self):
  self.g.decide('D1','reviewer','APPROVED'); self.assertFalse(self.t.closure_readiness('D1')['ready'])
 def test_complete_evidence_enables(self):
  self.t.add('E1','EVIDENCE','Proof','owner'); self.t.link('D1','E1','owner'); self.t.complete('E1','owner','sha256:abc')
  self.g.decide('D1','reviewer','APPROVED'); self.assertTrue(self.t.closure_readiness('D1')['ready'])
 def test_open_action_blocks(self):
  self.t.add('E1','EVIDENCE','Proof','owner'); self.t.link('D1','E1','owner'); self.t.complete('E1','owner','ref')
  self.t.add('A1','ACTION','Fix','owner'); self.t.link('D1','A1','owner'); self.g.decide('D1','reviewer','APPROVED')
  self.assertFalse(self.t.closure_readiness('D1')['ready']); self.t.complete('A1','owner','ticket:123'); self.assertTrue(self.t.closure_readiness('D1')['ready'])
 def test_audit_tamper_blocks_write(self):
  self.g.db.execute("UPDATE audit SET actor='forged' WHERE seq=1"); self.g.db.commit()
  with self.assertRaises(ValueError): self.t.add('A1','ACTION','Fix','owner')
 def test_self_approval_still_blocked(self):
  with self.assertRaises(ValueError): self.g.decide('D1','author','APPROVED')
if __name__=='__main__': unittest.main()
