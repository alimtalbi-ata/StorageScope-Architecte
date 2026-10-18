import unittest
from graph_layout import minimap_viewport,route_obstacles

class TestV478(unittest.TestCase):
    def test_viewport_clamped_size(self):
        w,h,b=minimap_viewport(1000,1000,300,300,999,999)
        self.assertAlmostEqual(b[2]-b[0],w*.3)
        self.assertAlmostEqual(b[3]-b[1],h*.3)
        self.assertAlmostEqual(b[2],w)
    def test_small_content(self):
        w,h,b=minimap_viewport(100,100,300,300)
        self.assertEqual(b,(0,0,w,h))
    def test_route_collision(self):
        self.assertEqual(route_obstacles([[(0,5),(20,5)]],[(5,0,10,10)]),[(0,0)])
    def test_route_clear(self):
        self.assertEqual(route_obstacles([[(0,0),(0,20)]],[(5,5,10,10)]),[])
    def test_invalid_clearance(self):
        with self.assertRaises(ValueError):route_obstacles([],[],clearance=-1)
