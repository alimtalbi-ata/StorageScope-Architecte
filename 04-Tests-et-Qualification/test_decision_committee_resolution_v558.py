import json, tempfile, unittest
from pathlib import Path
from decision_committee_resolution_v558 import CommitteeResolutionStore,export_resolutions
from decision_integrity_v540 import consistency_report

class CommitteeResolutionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.store=CommitteeResolutionStore(str(Path(self.temp.name)/'db.sqlite'))
  self.store.create('D1','Storage','Alice','2026-11-01','REF')
 def resolve(self,**kw):
  return self.store.resolve('D1','Alice','2026-10-16',kw.get('verdict','APPROVE'),'Décision humaine')
 def test_approve(self):self.assertTrue(self.resolve()['human_recorded'])
 def test_reject(self):self.assertEqual(self.resolve(verdict='REJECT')['decision_id'],'D1')
 def test_defer(self):self.assertEqual(self.resolve(verdict='DEFER')['decision_id'],'D1')
 def test_invalid_verdict(self):
  with self.assertRaises(ValueError):self.resolve(verdict='AUTO')
 def test_missing_decision(self):
  with self.assertRaises(KeyError):self.store.resolve('D9','Alice','2026-10-16','APPROVE','ok')
 def test_invalid_date(self):
  with self.assertRaises(ValueError):self.store.resolve('D1','Alice','bad','APPROVE','ok')
 def test_empty_actor(self):
  with self.assertRaises(ValueError):self.store.resolve('D1',' ','2026-10-16','APPROVE','ok')
 def test_audit_consistency(self):
  self.resolve();self.assertTrue(consistency_report(self.store)['consistent'])
 def test_history(self):
  self.resolve();self.resolve(verdict='DEFER');self.assertEqual(len(self.store.resolutions('D1')),2)
 def test_export(self):
  self.resolve();p=Path(self.temp.name)/'out.json';export_resolutions(self.store,p)
  self.assertEqual(len(json.loads(p.read_text())['resolutions']),1)
 def test_tampering(self):
  self.resolve()
  with self.store._connect() as db:db.execute("UPDATE committee_resolutions SET verdict='REJECT'")
  with self.assertRaises(ValueError):self.store.resolutions()
 def test_no_activation(self):self.assertFalse(self.resolve()['production_activation'])
