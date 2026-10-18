import random
import unittest
from graph_layout import ObstacleBucketIndex, _fast_route_hits_rect, scalable_obstacle_routes

class ObstacleIndexTests(unittest.TestCase):
    def test_random_equivalence(self):
        rng = random.Random(495)
        rects = [(x,y,x+40,y+30) for x,y in ((rng.randrange(-500,500),rng.randrange(-500,500)) for _ in range(200))]
        idx = ObstacleBucketIndex(rects)
        for _ in range(100):
            x,y = rng.randrange(-700,700),rng.randrange(-700,700)
            path = [(x,y),(x+100,y),(x+100,y+130)]
            self.assertEqual(idx.query(path), {i for i,r in enumerate(rects) if _fast_route_hits_rect(path,r)})
    def test_long_path_fallback(self):
        rects = [(-20,-20,20,20),(1_000_000,-20,1_000_040,20)]
        idx=ObstacleBucketIndex(rects,10)
        self.assertEqual(idx.query([(-2_000_000,0),(2_000_000,0)]),{0,1})
    def test_wide_rectangle(self):
        idx=ObstacleBucketIndex([(-100000,-5,100000,5)],10)
        self.assertEqual(idx.query([(0,-10),(0,10)]),{0})
    def test_router_deterministic(self):
        positions=[(str(i), i*25, (i%7)*90+180) for i in range(35)]
        self.assertEqual(scalable_obstacle_routes(positions,0),scalable_obstacle_routes(positions,0))
