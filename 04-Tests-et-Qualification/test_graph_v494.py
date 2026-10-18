import random
import unittest
from graph_layout import RecentSegmentIndex, _indexed_interference, _route_segments, scalable_obstacle_routes

class RecentSegmentIndex494(unittest.TestCase):
    def test_equivalence_randomized(self):
        rng=random.Random(494)
        for _ in range(80):
            paths=[]
            for _ in range(rng.randrange(1,25)):
                x,y=rng.randrange(-100,100),rng.randrange(-100,100)
                paths.append([(x,y),(x,y+rng.randrange(-80,80)),(x+rng.randrange(-80,80),y+rng.randrange(-80,80))])
            segments=[_route_segments(p) for p in paths]
            candidate=paths[-1]
            self.assertEqual(_indexed_interference(segments,candidate),RecentSegmentIndex(segments).score(candidate))
    def test_strict_endpoints_and_multiplicity(self):
        prior=[_route_segments([(0,0),(0,10),(10,10)])]*3
        for path in [[(-5,10),(5,10)], [(-5,5),(5,5)], [(0,0),(0,10)]]:
            self.assertEqual(_indexed_interference(prior,path),RecentSegmentIndex(prior).score(path))
    def test_routes_deterministic(self):
        p=[(str(i),i*135,145+(i%6)*90) for i in range(60)]
        self.assertEqual(scalable_obstacle_routes(p,0),scalable_obstacle_routes(p,0))
