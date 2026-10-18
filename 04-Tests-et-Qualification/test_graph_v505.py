import random
import unittest
from graph_layout import (_candidate_may_touch_rect, _fast_route_hits_rect,
                          PartialGeometryRoutingCache, scalable_obstacle_routes)

class GeometryPrefilterTests(unittest.TestCase):
    def test_never_rejects_true_collision(self):
        rng = random.Random(505)
        for _ in range(1500):
            x,y = rng.randrange(-500,500),rng.randrange(-500,500)
            path = [(0,0),(0,y),(x,y),(x,0)]
            a,b = rng.randrange(-500,500),rng.randrange(-500,500)
            rect = (a,b,a+rng.randrange(1,120),b+rng.randrange(1,120))
            if _fast_route_hits_rect(path,rect):
                self.assertTrue(_candidate_may_touch_rect(path,rect))

    def test_disjoint_box_rejected(self):
        self.assertFalse(_candidate_may_touch_rect([(0,0),(0,20),(20,20)],(30,30,40,40)))

    def test_large_graph_equivalent_to_full(self):
        old=[(str(i),400+i*240,350) for i in range(513)]
        cache=PartialGeometryRoutingCache()
        cache.route(old,100,recent_routes=0)
        new=list(old); new[250]=(new[250][0],new[250][1]+20,new[250][2])
        self.assertEqual(cache.route(new,100,recent_routes=0),scalable_obstacle_routes(new,100,recent_routes=0))
        self.assertGreaterEqual(cache.validation_skips,0)

    def test_middle_change_matches_full(self):
        old=[(str(i),400+(i%25)*440,350+(i//25)*300) for i in range(250)]
        cache=PartialGeometryRoutingCache()
        cache.route(old,100,recent_routes=8)
        new=list(old)
        new[120]=(new[120][0],new[120][1]+20,new[120][2])
        self.assertEqual(cache.route(new,100,recent_routes=8),
                         scalable_obstacle_routes(new,100,recent_routes=8))

if __name__=='__main__': unittest.main()
