import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class TimingDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.base = [(str(i), i*250, 250) for i in range(40)]

    def test_timing_and_bounded_samples(self):
        c = PartialGeometryRoutingCache(capacity=1)
        c.route(self.base, 0, recent_routes=8)
        for i in range(1,17):
            positions = list(self.base)
            positions[10] = ('edit', 2500+i, 250)
            self.assertEqual(c.route(positions,0,recent_routes=8), scalable_obstacle_routes(positions,0,recent_routes=8))
        self.assertEqual(c.routing_attempts,17)
        self.assertGreater(c.routing_time_seconds,0)
        self.assertLessEqual(len(c.workload_timing[(0,1,8)]),12)
        self.assertGreaterEqual(c.last_validation_fraction,0)

    def test_hit_does_not_change_timing(self):
        c=PartialGeometryRoutingCache()
        c.route(self.base,0)
        n=c.routing_attempts
        t=c.routing_time_seconds
        c.route(self.base,0)
        self.assertEqual((n,t),(c.routing_attempts,c.routing_time_seconds))

    def test_skipped_validation_has_zero_fraction(self):
        c=PartialGeometryRoutingCache(capacity=1)
        c.route(self.base,0,recent_routes=8)
        p=list(self.base);p[10]=('new',2550,250)
        c.route(p,0,recent_routes=8)
        c.validation_budget=0
        q=list(self.base);q[10]=('new',2570,250)
        c.route(q,0,recent_routes=8)
        self.assertEqual(c.last_validation_fraction,0)

if __name__ == '__main__': unittest.main()
