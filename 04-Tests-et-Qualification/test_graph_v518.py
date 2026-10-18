import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class AdaptiveEditGateTests(unittest.TestCase):
    def test_default_limit_preserved(self):
        c = PartialGeometryRoutingCache()
        self.assertTrue(c._should_full_route_for_edits(8, 100, 8))
        self.assertFalse(c._should_full_route_for_edits(7, 100, 8))

    def test_measured_gate_is_conservative(self):
        c = PartialGeometryRoutingCache()
        c.high_edit_threshold = 20
        c.high_edit_min_edits = 4
        c.high_edit_ratio_threshold = .05
        key = (1, 6, 8)
        c.workload_timing[key] = [{'validation_seconds': .030, 'routing_seconds': .010, 'reused': 0} for _ in range(3)]
        self.assertTrue(c._should_full_route_for_edits(6, 100, 8))
        self.assertEqual(c.high_edit_adaptive_decisions, 1)
        self.assertFalse(c._should_full_route_for_edits(6, 1000, 8))

    def test_reuse_prevents_adaptive_fallback(self):
        c = PartialGeometryRoutingCache()
        c.high_edit_threshold = 20
        c.high_edit_min_edits = 4
        c.high_edit_ratio_threshold = .05
        c.workload_timing[(1, 6, 8)] = [{'validation_seconds': .03, 'routing_seconds': .01, 'reused': 1} for _ in range(3)]
        self.assertFalse(c._should_full_route_for_edits(6, 100, 8))

    def test_route_equality(self):
        base = [(str(i), i * 250, 250) for i in range(40)]
        edited = list(base)
        for i in range(10, 18): edited[i] = (str(i), i*250+5, 250)
        c = PartialGeometryRoutingCache(capacity=1)
        c.route(base, 0, recent_routes=8)
        self.assertEqual(c.route(edited, 0, recent_routes=8), scalable_obstacle_routes(edited, 0, recent_routes=8))
