import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class ActualReuseTelemetryTests(unittest.TestCase):
    def test_cold_stats(self):
        nodes=[(str(i), 260*i+300, 200) for i in range(12)]
        cache=PartialGeometryRoutingCache(); cache.route(nodes, 0)
        self.assertEqual(cache.last_routing_stats, dict(prefix_reused=0,suffix_reused=0,recomputed=12))
    def test_multi_edit_accounting_and_equivalence(self):
        nodes=[(str(i), 260*i+300, 200) for i in range(36)]
        updated=list(nodes)
        for i in (19,30):
            a,x,y=updated[i];updated[i]=(a,x+12,y)
        cache=PartialGeometryRoutingCache();cache.route(nodes,0,recent_routes=8)
        result=cache.route(updated,0,recent_routes=8)
        self.assertEqual(result,scalable_obstacle_routes(updated,0,recent_routes=8))
        stats=cache.last_routing_stats
        self.assertEqual(sum(stats.values()),len(updated))
        self.assertGreater(stats['prefix_reused'],0)
    def test_candidate_reuse_not_overcounted(self):
        nodes=[(str(i),260*i+300,200) for i in range(40)]
        updated=list(nodes);updated[5]=('5',updated[5][1]+18,200)
        cache=PartialGeometryRoutingCache();cache.route(nodes,0,recent_routes=24)
        self.assertEqual(cache.route(updated,0,recent_routes=24),scalable_obstacle_routes(updated,0,recent_routes=24))
        self.assertEqual(cache.suffix_reuses,cache.last_routing_stats['suffix_reused'])
