import unittest
from governance import Governance
from cursor_pagination import decision_page
class CursorTests(unittest.TestCase):
 def setUp(self):
  self.g=Governance(':memory:')
  # Ensure the historical cursor fixture closes its in-memory SQLite handle.
  self.addCleanup(self.g.close)
  for i in range(105):self.g.propose(f'D-{i:03}','title','rationale','author')
 def test_no_duplicates_and_complete(self):
  ids=[];cursor=None
  while True:
   r=decision_page(self.g,25,cursor);ids.extend(x['id'] for x in r['items'])
   if not r['has_next']:break
   cursor=r['next_cursor']
  self.assertEqual(ids,[f'D-{i:03}' for i in range(105)])
 def test_cursor_invalid(self):
  for cursor in ('not-json','', 'e30'):
   with self.assertRaises(ValueError):decision_page(self.g,cursor=cursor)
 def test_reject_bool_limit(self):
  with self.assertRaises(ValueError):decision_page(self.g,True)
 def test_audit_tamper(self):
  self.g.db.execute("UPDATE audit SET actor='tampered' WHERE seq=1")
  with self.assertRaises(ValueError):decision_page(self.g)
if __name__=='__main__':unittest.main()
