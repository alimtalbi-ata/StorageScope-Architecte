import sqlite3, tempfile, unittest
from pathlib import Path
from graph_prepare import prepare_graph
from route_scheduler import RouteCancelled

class PreparationTests(unittest.TestCase):
    def test_readonly_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'test.sqlite3'
            con=sqlite3.connect(db)
            con.executescript('CREATE TABLE decisions(id TEXT,title TEXT,status TEXT,author TEXT,approver TEXT);CREATE TABLE reservations(id TEXT,decision_id TEXT,description TEXT,blocking INTEGER,status TEXT,owner TEXT);CREATE TABLE artifacts(id TEXT,kind TEXT,title TEXT,state TEXT,owner TEXT,reference TEXT);CREATE TABLE artifact_links(decision_id TEXT,artifact_id TEXT);')
            con.execute('INSERT INTO decisions VALUES (?,?,?,?,?)',('D1','Title','APPROVED','A','B'))
            con.execute('INSERT INTO reservations VALUES (?,?,?,?,?,?)',('R1','D1','text',1,'OPEN','A'))
            con.commit();con.close()
            result=prepare_graph((str(db),'D1','TOUS','',(),60,800))
            self.assertEqual(result[0],'APPROVED')
            self.assertEqual(len(result[1]),1)
    def test_cancelled(self):
        with self.assertRaises(RouteCancelled):prepare_graph(('unused','D','TOUS','',(),60,800),lambda:True)
    def test_missing_db_does_not_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'missing.sqlite3'
            with self.assertRaises(sqlite3.OperationalError):prepare_graph((str(path),'D','TOUS','',(),60,800))
            self.assertFalse(path.exists())
if __name__=='__main__':unittest.main()
