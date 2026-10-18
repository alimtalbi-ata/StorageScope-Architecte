import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class CostGateNoiseTests(unittest.TestCase):
    def test_submillisecond_observations_do_not_disable_partial(self):
        c=PartialGeometryRoutingCache(capacity=2)
        base=[(str(i),i*250,250) for i in range(40)]
        c.route(base,0,recent_routes=8)
        c.workload_timing[(0,1,8)]=[dict(validation_seconds=.0002,routing_seconds=.00001,reused=0) for _ in range(3)]
        modified=list(base);modified[10]=('edit',2551,250)
        self.assertEqual(c.route(modified,0,recent_routes=8),scalable_obstacle_routes(modified,0,recent_routes=8))
        self.assertEqual(c.cost_gate_skips,0)
    def test_real_cost_evidence_still_enables_gate(self):
        c=PartialGeometryRoutingCache(capacity=2)
        base=[(str(i),i*250,250) for i in range(40)]
        c.route(base,0,recent_routes=8)
        c.workload_timing[(0,1,8)]=[dict(validation_seconds=.003,routing_seconds=.001,reused=0) for _ in range(3)]
        modified=list(base);modified[10]=('edit',2551,250)
        self.assertEqual(c.route(modified,0,recent_routes=8),scalable_obstacle_routes(modified,0,recent_routes=8))
        self.assertEqual(c.cost_gate_skips,1)
    def test_configured_threshold_is_exposed(self):
        self.assertEqual(PartialGeometryRoutingCache().cost_gate_min_validation_seconds,.001)
