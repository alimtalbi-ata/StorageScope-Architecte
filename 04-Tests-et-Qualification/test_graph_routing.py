import unittest
from graph_layout import orthogonal_routes,minimap_geometry
class RoutingTests(unittest.TestCase):
 def test_routes(self):
  p=[(('A','1','OPEN',False),110,140),(('B','2','OPEN',True),350,220)]
  r=orthogonal_routes(p,240)
  self.assertEqual(len(r),2)
  self.assertEqual(r[0][-1],(110,116))
  self.assertEqual(r[1][0],(240,68))
 def test_empty(self):self.assertEqual(orthogonal_routes([],100),[])
 def test_invalid(self):
  with self.assertRaises(ValueError):orthogonal_routes([],100,branch_y=60)
 def test_minimap(self):
  w,h,box=minimap_geometry(1000,500,250,200,180,115,100,50)
  self.assertEqual((w,h),(180,90))
  self.assertGreater(box[2],box[0])
 def test_minimap_clamp(self):
  _,_,box=minimap_geometry(1000,1000,200,200,scroll_x=9999,scroll_y=9999)
  self.assertLessEqual(box[2],180);self.assertLessEqual(box[3],115)
 def test_minimap_invalid(self):
  with self.assertRaises(ValueError):minimap_geometry(0,500,200,200)
