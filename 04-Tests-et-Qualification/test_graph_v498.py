import random
import unittest
from graph_layout import ObstacleBucketIndex, scalable_obstacle_routes

class SegmentCacheTests(unittest.TestCase):
    def test_cache_equivalence_random(self):
        rng=random.Random(498)
        rectangles=[(x,y,x+80,y+35) for x,y in ((rng.randrange(-300,300),rng.randrange(-200,200)) for _ in range(150))]
        index=ObstacleBucketIndex(rectangles)
        cache={}
        for _ in range(150):
            x,y=rng.randrange(-400,400),rng.randrange(-300,300)
            path=[(0,0),(0,y),(x,y),(x,0)]
            self.assertEqual(index.query(path),index.query(path,cache))
            self.assertEqual(index.query(list(reversed(path))),index.query(list(reversed(path)),cache))
    def test_cache_bound(self):
        index=ObstacleBucketIndex([(0,0,20,20)])
        cache={}
        for i in range(2300):
            index.query([(i,0),(i,30)],cache)
        self.assertLessEqual(len(cache),2048)
    def test_repeat_determinism(self):
        positions=[(str(i),(i%17)*230,160+(i//17)*85) for i in range(150)]
        self.assertEqual(scalable_obstacle_routes(positions,120),scalable_obstacle_routes(positions,120))
