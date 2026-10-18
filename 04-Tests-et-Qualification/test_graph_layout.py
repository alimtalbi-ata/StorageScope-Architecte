import unittest
from graph_layout import layout_nodes,filter_nodes

class GraphLayoutTests(unittest.TestCase):
 def test_nonoverlap(self):
  positions,w,h=layout_nodes([('ACTION',str(i),'OPEN',False) for i in range(50)],850,3)
  self.assertEqual(len(positions),50)
  for i,(_,x,y) in enumerate(positions):
   for _,xx,yy in positions[i+1:]:
    self.assertTrue(abs(x-xx)>=190 or abs(y-yy)>=48)
 def test_filter_kind(self):
  nodes=[('ACTION','A1','OPEN',True),('ADR','B1','DONE',False)]
  self.assertEqual(len(filter_nodes(nodes,['ADR'])),1)
 def test_filter_text(self):
  self.assertEqual(len(filter_nodes([('ACTION','INC-1','OPEN',False)],query='inc-1')),1)
 def test_empty(self):
  self.assertEqual(layout_nodes([],550,2)[0],[])
 def test_validation(self):
  with self.assertRaises(ValueError):layout_nodes([],200)
  with self.assertRaises(ValueError):layout_nodes([],600,0)
