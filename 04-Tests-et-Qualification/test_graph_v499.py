import unittest
from collections import OrderedDict
from graph_layout import ObstacleBucketIndex, scalable_obstacle_routes

class LRUObstacleTests(unittest.TestCase):
    def test_recent_segment_survives_eviction(self):
        idx=ObstacleBucketIndex([(0,0,20,20)])
        cache=OrderedDict()
        a=[(10,-10),(10,30)]
        idx.query(a,cache)
        for n in range(2047):
            idx.query([(100+n,0),(100+n,30)],cache)
        idx.query(a,cache)
        idx.query([(10000,0),(10000,30)],cache)
        self.assertIn(((10,-10),(10,30)),cache)
        self.assertEqual(len(cache),2048)
    def test_lru_matches_reference(self):
        idx=ObstacleBucketIndex([(i*7,i*3,i*7+18,i*3+18) for i in range(80)])
        cache=OrderedDict()
        for n in range(2400):
            path=[(n%500,-10),(n%500,300)]
            self.assertEqual(idx.query(path),idx.query(path,cache))
    def test_route_determinism(self):
        p=[(str(i),(i%21)*220,160+(i//21)*90) for i in range(220)]
        self.assertEqual(scalable_obstacle_routes(p,110),scalable_obstacle_routes(p,110))
