"""Legacy HLD/LLD audit consistency under concurrent writers."""
import tempfile, threading, unittest, sqlite3
from pathlib import Path
from governance import Governance

class LegacyAtomicV600(unittest.TestCase):
    def test_parallel_proposals_keep_chain(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'legacy.db'; barrier=threading.Barrier(5); errors=[]
            def worker(i):
                g=Governance(path)
                try:
                    barrier.wait(timeout=10)
                    g.propose(f'D-{i}','SAN design','redundancy','architect')
                except Exception as e:errors.append(e)
                finally:g.close()
            threads=[threading.Thread(target=worker,args=(i,)) for i in range(5)]
            for t in threads:t.start()
            for t in threads:t.join(timeout=15)
            self.assertFalse(errors)
            g=Governance(path)
            try:
                self.assertTrue(g.verify_audit())
                self.assertEqual(g.db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],5)
            finally:g.close()
    def test_failed_proposal_rolls_back_audit(self):
        with tempfile.TemporaryDirectory() as d:
            g=Governance(Path(d)/'db.sqlite')
            try:
                g.propose('D','title','reason','author')
                with self.assertRaises(sqlite3.IntegrityError):g.propose('D','title','reason','author')
                self.assertTrue(g.verify_audit())
                self.assertEqual(g.db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],1)
            finally:g.close()
    def test_rejected_approval_preserves_state(self):
        with tempfile.TemporaryDirectory() as d:
            g=Governance(Path(d)/'db.sqlite')
            try:
                g.propose('D','title','reason','author')
                with self.assertRaises(ValueError):g.decide('D','author','APPROVED')
                self.assertTrue(g.verify_audit())
                self.assertEqual(g.db.execute('SELECT status FROM decisions').fetchone()[0],'PROPOSED')
            finally:g.close()
    def test_parallel_reservations_preserve_chain(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'db.sqlite';g=Governance(path);g.propose('D','title','reason','author');g.close()
            barrier=threading.Barrier(4); errors=[]
            def worker(i):
                local=Governance(path)
                try:
                    barrier.wait(timeout=10);local.add_reservation(f'R-{i}','D','risk','ops')
                except Exception as e:errors.append(e)
                finally:local.close()
            threads=[threading.Thread(target=worker,args=(i,)) for i in range(4)]
            for t in threads:t.start()
            for t in threads:t.join(timeout=15)
            self.assertFalse(errors)
            g=Governance(path)
            try:self.assertTrue(g.verify_audit());self.assertEqual(g.db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],5)
            finally:g.close()
    def test_transaction_helper_used_for_mutations(self):
        source=(Path(__file__).parent/'governance.py').read_text()
        self.assertEqual(source.count('with self._write_transaction():'),4)
        self.assertIn('BEGIN IMMEDIATE',source)

if __name__=='__main__':unittest.main()
