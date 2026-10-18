import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class AdaptiveProbeTests(unittest.TestCase):
    def setUp(self):
        self.base = [(str(i), i*250, 250) for i in range(40)]
        self.workload = (0,1,8)

    def change(self, step):
        p = list(self.base)
        p[10] = ('changed', self.base[10][1]+step, 250)
        return p

    def test_failed_probe_backs_off(self):
        c = PartialGeometryRoutingCache(capacity=1)
        c.route(self.base,0,recent_routes=8)
        c.reuse_history[self.workload] = [0,0,0]
        c.validation_budget = 1  # force full routing on probe
        for i in range(1,6):
            p=self.change(i)
            self.assertEqual(c.route(p,0,recent_routes=8),scalable_obstacle_routes(p,0,recent_routes=8))
        self.assertEqual(c.probe_failures,1)
        self.assertEqual(c._probe_intervals[self.workload],10)
        for i in range(6,15): c.route(self.change(i),0,recent_routes=8)
        self.assertEqual(c.profitability_probes,1)
        c.route(self.change(15),0,recent_routes=8)
        self.assertEqual(c.profitability_probes,2)
        self.assertEqual(c._probe_intervals[self.workload],16)

    def test_success_resets_interval(self):
        c=PartialGeometryRoutingCache(capacity=1)
        c.route(self.base,0,recent_routes=8)
        c.reuse_history[self.workload]=[0,0,0]
        c._probe_intervals[self.workload]=2
        c.route(self.change(1),0,recent_routes=8)
        c.route(self.change(2),0,recent_routes=8)
        self.assertEqual(c.probe_successes,1)
        self.assertEqual(c._probe_intervals[self.workload],5)

    def test_adaptive_state_is_instance_local(self):
        a,b=PartialGeometryRoutingCache(),PartialGeometryRoutingCache()
        a._probe_intervals[self.workload]=16
        self.assertNotIn(self.workload,b._probe_intervals)

if __name__ == '__main__': unittest.main()
