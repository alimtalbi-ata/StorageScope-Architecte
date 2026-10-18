import unittest
from graph_layout import _fast_interference, _indexed_interference, _route_segments, scalable_obstacle_routes

class CachedSegments493(unittest.TestCase):
    def test_crossing(self):
        prior=[[(0,0),(0,10),(10,10)],[(5,-5),(5,15),(15,15)]]
        candidate=[(-5,5),(15,5),(15,20)]
        self.assertEqual(_fast_interference(prior,candidate),_indexed_interference([_route_segments(x) for x in prior],candidate))
    def test_shared_segments(self):
        prior=[[(0,0),(0,20),(10,20)]]
        candidate=[(0,0),(0,15),(20,15)]
        self.assertEqual(_fast_interference(prior,candidate),_indexed_interference([_route_segments(x) for x in prior],candidate))
    def test_deterministic(self):
        p=[(str(i),i*130,150+(i%4)*100) for i in range(35)]
        self.assertEqual(scalable_obstacle_routes(p,0),scalable_obstacle_routes(p,0))
