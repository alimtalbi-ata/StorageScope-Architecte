import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class PeriodicProfitabilityProbeTests(unittest.TestCase):
    def test_rechecks_after_five_skips(self):
        cache = PartialGeometryRoutingCache(capacity=1)
        base = [(str(i), i*250, 250) for i in range(40)]
        cache.route(base, 0, recent_routes=8)
        workload = (0, 1, 8)
        cache.reuse_history[workload] = [0, 0, 0]
        for step in range(1, 6):
            changed = list(base)
            changed[10] = ('edited', base[10][1]+step, 250)
            result = cache.route(changed, 0, recent_routes=8)
            self.assertEqual(result, scalable_obstacle_routes(changed, 0, recent_routes=8))
        self.assertEqual(cache.profitability_skips, 4)
        self.assertEqual(cache.profitability_probes, 1)

    def test_recovery_when_probe_finds_reuse(self):
        cache = PartialGeometryRoutingCache(capacity=1)
        base = [(str(i), i*250, 250) for i in range(40)]
        cache.route(base, 0, recent_routes=8)
        workload = (0, 1, 8)
        cache.reuse_history[workload] = [0, 0, 0]
        for step in range(1, 6):
            changed = list(base)
            changed[10] = ('edited', base[10][1]+step, 250)
            cache.route(changed, 0, recent_routes=8)
        self.assertGreater(cache.last_routing_stats['prefix_reused'], 0)
        self.assertGreater(cache.reuse_history[workload][-1], 0)
        changed = list(base)
        changed[10] = ('edited', base[10][1]+7, 250)
        previous = cache.profitability_skips
        cache.route(changed, 0, recent_routes=8)
        self.assertEqual(cache.profitability_skips, previous)

    def test_isolation(self):
        a = PartialGeometryRoutingCache()
        b = PartialGeometryRoutingCache()
        a._profitability_skip_streak[(0,1,8)] = 4
        self.assertEqual(b._profitability_skip_streak, {})

if __name__ == '__main__':
    unittest.main()
