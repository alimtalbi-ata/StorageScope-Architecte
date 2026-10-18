import unittest
from graph_layout import routed_connections,minimap_scroll_fraction
class Routing477Tests(unittest.TestCase):
 def test_empty(self):self.assertEqual(routed_connections([],200),[])
 def test_distinct_tracks(self):
  pos=[(('A',str(i),'OPEN',False),120+i*220,140) for i in range(5)]
  paths=routed_connections(pos,500)
  self.assertEqual(len(set(p[1][1] for p in paths)),5)
  self.assertTrue(all(p[-1][1]==116 for p in paths))
  self.assertTrue(all(68<p[1][1]<116 for p in paths))
 def test_stable(self):
  p=[(('A','1','OPEN',False),100,140)]
  self.assertEqual(routed_connections(p,250),routed_connections(p,250))
 def test_invalid(self):
  with self.assertRaises(ValueError):routed_connections([(('A','1','',False),10,100)],200)
 def test_minimap_clamp(self):
  self.assertEqual(minimap_scroll_fraction(-100,180,1000,200),0)
  self.assertLessEqual(minimap_scroll_fraction(1000,180,1000,200),1)
 def test_minimap_small_content(self):self.assertEqual(minimap_scroll_fraction(30,180,100,200),0)
 def test_minimap_invalid(self):
  with self.assertRaises(ValueError):minimap_scroll_fraction(0,0,100,20)
if __name__=='__main__':unittest.main()
