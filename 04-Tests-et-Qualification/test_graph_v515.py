import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class CostProbeTests(unittest.TestCase):
    def setUp(self):
        self.base=[(str(i), i*250,250) for i in range(40)]
        self.workload=(0,1,8)
    def cache(self):
        c=PartialGeometryRoutingCache(capacity=2)
        c.route(self.base,0,recent_routes=8)
        c.workload_timing[self.workload]=[dict(validation_seconds=.3,routing_seconds=.01,reused=0) for _ in range(3)]
        return c
    def test_bounded_cost_gate_probe(self):
        c=self.cache()
        for i in range(1,6):
            modified=list(self.base);modified[10]=('edit',2550+i,250)
            self.assertEqual(c.route(modified,0,recent_routes=8),scalable_obstacle_routes(modified,0,recent_routes=8))
        self.assertEqual(c.cost_gate_skips,4)
        self.assertEqual(c.cost_gate_probes,1)
    def test_probe_does_not_bypass_correctness(self):
        c=self.cache();c._cost_gate_streak[self.workload]=4
        modified=list(self.base);modified[10]=('edit',2551,250)
        self.assertEqual(c.route(modified,0,recent_routes=8),scalable_obstacle_routes(modified,0,recent_routes=8))
        self.assertEqual(c.cost_gate_probes,1)
    def test_favorable_evidence_resets_streak(self):
        c=self.cache();c._cost_gate_streak[self.workload]=3
        c.workload_timing[self.workload][-1]['reused']=1
        modified=list(self.base);modified[10]=('edit',2551,250)
        c.route(modified,0,recent_routes=8)
        self.assertEqual(c.cost_gate_skips,0)
        self.assertNotIn(self.workload,c._cost_gate_streak)
if __name__=='__main__':unittest.main()
