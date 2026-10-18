import json
import tempfile
import unittest
from pathlib import Path
from campaign_history_v526 import CampaignHistory

def campaign(i,gain=.12):
    return {'id':str(i),'pairs':[{'id':str(j),'nodes':100,'edits':3,'spacing':100,'baseline_seconds':.1,'candidate_seconds':.1*(1-gain),'routes_equal':True} for j in range(12)]}
class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=CampaignHistory(Path(self.tmp.name)/'history.db')
    def test_empty(self): self.assertEqual(self.db.report()['reason'],'no_campaigns')
    def test_idempotent(self):
        self.assertTrue(self.db.add(campaign(1)));self.assertFalse(self.db.add(campaign(1)))
    def test_immutable_conflict(self):
        self.db.add(campaign(1))
        with self.assertRaises(ValueError): self.db.add(campaign(1,.2))
    def test_stable_report(self):
        for i in range(3): self.db.add(campaign(i))
        self.assertEqual(self.db.report()['selected_policy'],'candidate_measured')
        self.assertFalse(self.db.report()['production_activation'])
    def test_regression_alert(self):
        for i,g in enumerate((.12,.12,-.2)):self.db.add(campaign(i,g))
        self.assertEqual(self.db.report()['selected_policy'],'default')
        self.assertTrue(self.db.report()['alerts'])
    def test_integrity_tamper(self):
        self.db.add(campaign(1))
        with self.db._connect() as conn:conn.execute('UPDATE campaigns SET payload=? WHERE id=?',('{}','1'))
        with self.assertRaises(ValueError):self.db.list()
    def test_export(self):
        self.db.add(campaign(1));out=Path(self.tmp.name)/'report.json'
        self.db.export_json(out)
        self.assertEqual(json.loads(out.read_text())['campaign_count'],1)
    def test_invalid_limit(self):
        with self.assertRaises(ValueError):self.db.list(True)
if __name__=='__main__':unittest.main()
