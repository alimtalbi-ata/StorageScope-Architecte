"""SQLite governance race and UI layout regressions. Author: Abdelhalim Talbi."""
import tempfile, threading, unittest
from pathlib import Path
from decision_governance_v537 import GovernanceStore

class GovernanceConcurrencyV596(unittest.TestCase):
    def test_create_same_id_once(self):
        with tempfile.TemporaryDirectory() as d:
            store=GovernanceStore(Path(d)/'gov.db'); barrier=threading.Barrier(4); results=[]
            def worker():
                barrier.wait()
                try: store.create('D-1','Subject','Owner','2026-12-31','Evidence'); results.append('ok')
                except ValueError: results.append('duplicate')
            threads=[threading.Thread(target=worker) for _ in range(4)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertEqual(results.count('ok'),1)
            self.assertEqual(results.count('duplicate'),3)
            self.assertEqual(len(store.report()['audit']),1)
    def test_followup_once_under_contention(self):
        with tempfile.TemporaryDirectory() as d:
            store=GovernanceStore(Path(d)/'gov.db');store.create('D-1','Subject','Owner','2026-01-01','Evidence')
            barrier=threading.Barrier(4); results=[]
            def worker():
                barrier.wait();results.append(store.followup('D-1','Architect','Reminder',today='2026-10-17'))
            threads=[threading.Thread(target=worker) for _ in range(4)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertEqual(results.count(True),1)
            self.assertEqual(results.count(False),3)
            self.assertEqual(len(store.governance_report()['followups']),1)
    def test_distinct_concurrent_decisions(self):
        with tempfile.TemporaryDirectory() as d:
            store=GovernanceStore(Path(d)/'gov.db');barrier=threading.Barrier(4);errors=[]
            def worker(i):
                try:barrier.wait();store.create(f'D-{i}','Subject','Owner','2026-12-31','Evidence')
                except Exception as exc:errors.append(exc)
            threads=[threading.Thread(target=worker,args=(i,)) for i in range(4)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertFalse(errors);self.assertEqual(len(store.report()['decisions']),4)
    def test_toolbar_sections(self):
        source=(Path(__file__).parent/'decision_workspace_ui_v543.py').read_text()
        self.assertIn("text='Comité et historique'",source)
        self.assertIn("text='Vues enregistrées'",source)
        self.assertIn('ttk.Entry(views_bar,textvariable=view_name',source)
    def test_view_commands_not_on_committee_bar(self):
        source=(Path(__file__).parent/'decision_workspace_ui_v543.py').read_text()
        for label in ('Enregistrer vue','Charger vue','Supprimer vue'):
            self.assertIn(f"ttk.Button(views_bar,text='{label}'",source)

if __name__=='__main__':unittest.main()
