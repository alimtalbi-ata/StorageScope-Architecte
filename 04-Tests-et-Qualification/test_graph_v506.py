import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class AdaptiveValidationTests(unittest.TestCase):
    def make(self,n):
        return [(str(i),400+i*260,350) for i in range(n)]
    def test_budget_skip_falls_back_exactly(self):
        old=self.make(30); cache=PartialGeometryRoutingCache()
        cache.route(old,100,recent_routes=0)
        cache.validation_budget=1
        new=list(old); new[20]=(new[20][0],new[20][1]+10,new[20][2])
        self.assertEqual(cache.route(new,100,recent_routes=0),scalable_obstacle_routes(new,100,recent_routes=0))
        self.assertGreater(cache.validation_skips,0)
    def test_large_graph_not_excluded_by_node_count(self):
        old=self.make(520); cache=PartialGeometryRoutingCache()
        cache.route(old,100,recent_routes=0)
        new=list(old); new[-1]=(new[-1][0],new[-1][1]+10,new[-1][2])
        self.assertEqual(cache.route(new,100,recent_routes=0),scalable_obstacle_routes(new,100,recent_routes=0))
        self.assertGreater(cache.validation_checks,0)
    def test_zero_budget_and_cancel(self):
        old=self.make(12); cache=PartialGeometryRoutingCache()
        cache.route(old,100,recent_routes=0)
        cache.validation_budget=0
        new=list(old); new[6]=(new[6][0],new[6][1]+15,new[6][2])
        self.assertEqual(cache.route(new,100,recent_routes=0),scalable_obstacle_routes(new,100,recent_routes=0))
        self.assertGreater(cache.validation_skips,0)
