import unittest
from graph_layout import grouped_nodes,layout_grouped

class GroupedGraphTests(unittest.TestCase):
 def setUp(self):
  self.nodes=[('ACTION',str(i),'OPEN',i==1) for i in range(100)]+[('ADR','A','DONE',False),('RÉSERVE','R','OPEN',True)]
 def test_group_counts(self):
  visible,groups,remaining=grouped_nodes(self.nodes,limit=60)
  self.assertEqual(dict(groups),{'RÉSERVE':1,'ADR':1,'ACTION':100})
  self.assertEqual(len(visible),60);self.assertEqual(remaining,42)
 def test_collapsed_critical(self):
  visible,groups,remaining=grouped_nodes(self.nodes,collapsed=('ACTION',))
  self.assertEqual(len(visible),3);self.assertEqual(remaining,0)
  self.assertIn(('GROUPE','ACTION','100 élément(s)',True),visible)
 def test_progressive(self):
  a,_,r=grouped_nodes(self.nodes,limit=60)
  b,_,r2=grouped_nodes(self.nodes,limit=120)
  self.assertEqual(b[:60],a);self.assertEqual(r,42);self.assertEqual(r2,0)
 def test_layout_nonoverlap(self):
  visible,_,_=grouped_nodes(self.nodes,limit=100)
  placed,_,_=layout_grouped(visible,850,3)
  for i,(_,x,y) in enumerate(placed):
   for _,xx,yy in placed[i+1:]:
    self.assertTrue(abs(x-xx)>=190 or abs(y-yy)>=48)
 def test_invalid_limits(self):
  for bad in (0,-1,True,10001):
   with self.assertRaises(ValueError):grouped_nodes(self.nodes,limit=bad)
 def test_empty(self):
  self.assertEqual(grouped_nodes([]),([],[],0))
