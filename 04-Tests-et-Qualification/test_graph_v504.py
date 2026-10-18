import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class RecentSuffixReuseTests(unittest.TestCase):
    def setUp(self):
        self.old = [(str(i), 500+i*450, 400) for i in range(48)]

    def test_reuse_after_recent_window(self):
        cache = PartialGeometryRoutingCache()
        cache.route(self.old, 100, recent_routes=4)
        changed = list(self.old)
        changed[5] = ('moved', changed[5][1]+30, 400)
        self.assertEqual(cache.route(changed, 100, recent_routes=4),
                         scalable_obstacle_routes(changed, 100, recent_routes=4))
        self.assertGreater(cache.suffix_reuses, 0)

    def test_reuse_with_full_recent_window(self):
        cache = PartialGeometryRoutingCache()
        cache.route(self.old, 100, recent_routes=24)
        changed = list(self.old)
        changed[5] = ('moved', changed[5][1]+30, 400)
        self.assertEqual(cache.route(changed, 100, recent_routes=24),
                         scalable_obstacle_routes(changed, 100, recent_routes=24))
        self.assertGreater(cache.suffix_reuses, 0)

    def test_reuse_only_when_prior_paths_match(self):
        old = [(str(i), 500+i*450, 400) for i in range(12)]
        cache = PartialGeometryRoutingCache()
        cache.route(old, 100, recent_routes=4)
        changed = list(old)
        changed[5] = ('moved', changed[5][1]+30, 400)
        self.assertEqual(cache.route(changed, 100, recent_routes=4),
                         scalable_obstacle_routes(changed, 100, recent_routes=4))

if __name__ == '__main__': unittest.main()
