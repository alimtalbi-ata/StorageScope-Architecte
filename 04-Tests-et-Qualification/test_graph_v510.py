import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class ProfitabilityTests(unittest.TestCase):
    def test_history_is_instance_local(self):
        a = PartialGeometryRoutingCache()
        b = PartialGeometryRoutingCache()
        a.reuse_history[(1, 1, 8)] = [0, 0, 0]
        self.assertEqual(b.reuse_history, {})

    def test_skip_does_not_change_result(self):
        positions = [('n'+str(i), i*240, 250) for i in range(40)]
        cache = PartialGeometryRoutingCache()
        cache.route(positions, 0, recent_routes=8)
        changed = list(positions)
        changed[-1] = ('last', changed[-1][1]+10, 250)
        cache.reuse_history[(0, 1, 8)] = [0, 0, 0]
        got = cache.route(changed, 0, recent_routes=8)
        expected = scalable_obstacle_routes(changed, 0, recent_routes=8)
        self.assertEqual(got, expected)
        self.assertEqual(cache.profitability_skips, 1)
        self.assertEqual(cache.last_routing_stats['suffix_reused'], 0)

    def test_positive_history_keeps_validation(self):
        positions = [('n'+str(i), i*240, 250) for i in range(40)]
        cache = PartialGeometryRoutingCache()
        cache.route(positions, 0, recent_routes=8)
        changed = list(positions)
        changed[-1] = ('last', changed[-1][1]+10, 250)
        cache.reuse_history[(0, 1, 8)] = [0, 0, 1]
        got = cache.route(changed, 0, recent_routes=8)
        self.assertEqual(got, scalable_obstacle_routes(changed, 0, recent_routes=8))
        self.assertEqual(cache.profitability_skips, 0)

if __name__ == '__main__':
    unittest.main()
