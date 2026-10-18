import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class CostGateTests(unittest.TestCase):
    def setUp(self):
        self.base=[(str(i),i*250,250) for i in range(40)]

    def test_expensive_zero_reuse_skips_safely(self):
        c=PartialGeometryRoutingCache(capacity=2)
        c.route(self.base,0,recent_routes=8)
        workload=(0,1,8)
        c.workload_timing[workload]=[dict(validation_seconds=.3,routing_seconds=.01,reused=0) for _ in range(3)]
        modified=list(self.base);modified[10]=('edit',2551,250)
        self.assertEqual(c.route(modified,0,recent_routes=8),scalable_obstacle_routes(modified,0,recent_routes=8))
        self.assertEqual(c.cost_gate_skips,1)

    def test_reuse_or_low_cost_keeps_validation(self):
        for reused,validation in [(1,.3),(0,.005)]:
            c=PartialGeometryRoutingCache(capacity=2)
            c.route(self.base,0,recent_routes=8)
            c.workload_timing[(0,1,8)]=[dict(validation_seconds=validation,routing_seconds=.01,reused=reused) for _ in range(3)]
            modified=list(self.base);modified[10]=('edit',2551,250)
            self.assertEqual(c.route(modified,0,recent_routes=8),scalable_obstacle_routes(modified,0,recent_routes=8))
            self.assertEqual(c.cost_gate_skips,0)

    def test_insufficient_evidence_does_not_skip(self):
        c=PartialGeometryRoutingCache(capacity=2)
        c.route(self.base,0,recent_routes=8)
        c.workload_timing[(0,1,8)]=[dict(validation_seconds=.3,routing_seconds=.01,reused=0) for _ in range(2)]
        modified=list(self.base);modified[10]=('edit',2551,250)
        c.route(modified,0,recent_routes=8)
        self.assertEqual(c.cost_gate_skips,0)

if __name__=='__main__': unittest.main()
