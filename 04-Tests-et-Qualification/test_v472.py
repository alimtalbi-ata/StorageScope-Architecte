import sqlite3
import unittest
from fast_dashboard import find_decisions

class SearchGraphTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE decisions(id TEXT,title TEXT,status TEXT,author TEXT)')
        self.db.executemany('INSERT INTO decisions VALUES(?,?,?,?)',[(f'D-{i:04}',f'Architecture {i}','PROPOSED','Abdelhalim') for i in range(650)])
        self.db.execute('INSERT INTO decisions VALUES(?,?,?,?)',('ID_%','Special % value','APPROVED','Auteur'))
    def tearDown(self):self.db.close()
    def test_search_beyond_picker_limit(self):
        self.assertEqual(find_decisions(self.db,'D-0649')[0]['id'],'D-0649')
    def test_literal_wildcards(self):
        self.assertEqual([x['id'] for x in find_decisions(self.db,'ID_%')],['ID_%'])
    def test_bounded(self):self.assertEqual(len(find_decisions(self.db,'Architecture',limit=17)),17)
    def test_invalid_limit(self):
        with self.assertRaises(ValueError):find_decisions(self.db,'D-',0)
    def test_empty(self):self.assertEqual(find_decisions(self.db,' '),[])
    def test_exact_first(self):self.assertEqual(find_decisions(self.db,'D-0010')[0]['id'],'D-0010')
