"""Regression tests for chronological governance integrity."""
import tempfile
import unittest
from pathlib import Path
from decision_governance_v537 import GovernanceStore
from decision_integrity_v540 import consistency_report
from decision_chronology_v550 import decision_chronology

class ChronologyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=GovernanceStore(Path(self.tmp.name)/'decisions.db')
        self.store.create('D1','Architecture','Alice','2030-01-01','REF-1')
    def tearDown(self):self.tmp.cleanup()
    def test_creation(self):
        result=decision_chronology(self.store,'D1')
        self.assertEqual(result['events'][0]['label'],'Création')
    def test_unknown(self):
        with self.assertRaises(KeyError):decision_chronology(self.store,'missing')
    def test_safe(self):self.assertFalse(decision_chronology(self.store,'D1')['production_activation'])
    def test_transition(self):
        self.store.transition('D1','IN_REVIEW','Alice','Review')
        self.assertEqual(decision_chronology(self.store,'D1')['events'][-1]['type'],'TRANSITION')
    def test_consistency(self):self.assertTrue(consistency_report(self.store)['consistent'])
    def test_illegal_transition_detected(self):
        self.store.transition('D1','IN_REVIEW','Alice','Review')
        with self.store._connect() as db:
            rows=db.execute('SELECT seq,payload FROM decision_audit ORDER BY seq').fetchall()
            import json,hashlib
            prev='0'*64
            for seq,raw in rows:
                event=json.loads(raw)
                if event['event']=='TRANSITION':event['to']='CLOSED'
                raw=json.dumps(event,sort_keys=True,ensure_ascii=False,separators=(',',':'))
                digest=hashlib.sha256((prev+raw).encode()).hexdigest()
                db.execute('UPDATE decision_audit SET payload=?,previous_hash=?,entry_hash=? WHERE seq=?',(raw,prev,digest,seq))
                prev=digest
        self.assertIn('illegal_transition',[i['code'] for i in consistency_report(self.store)['issues']])
    def test_unknown_event_detected(self):
        with self.store._connect() as db:
            self.store._append(db,'D1',{'event':'UNRECOGNIZED','id':'D1'})
        self.assertIn('unknown_audit_event',[i['code'] for i in consistency_report(self.store)['issues']])
    def test_out_of_order_creation_detected(self):
        with self.store._connect() as db:
            rows=db.execute('SELECT seq,payload FROM decision_audit ORDER BY seq').fetchall()
            import json,hashlib
            event={'event':'FOLLOWUP_RECORDED','id':'D1','due_date':'2030-01-01','actor':'A','note':'N'}
            original=json.loads(rows[0][1]); prev='0'*64
            for seq,obj in [(1,event),(2,original)]:
                raw=json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'))
                digest=hashlib.sha256((prev+raw).encode()).hexdigest()
                if seq==1:db.execute('UPDATE decision_audit SET payload=?,previous_hash=?,entry_hash=? WHERE seq=?',(raw,prev,digest,seq))
                else:db.execute('INSERT INTO decision_audit(seq,decision_id,payload,previous_hash,entry_hash) VALUES (?,?,?,?,?)',(seq,'D1',raw,prev,digest))
                prev=digest
        self.assertIn('creation_order_mismatch',[i['code'] for i in consistency_report(self.store)['issues']])

if __name__=='__main__':unittest.main()
