import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes

class HighEditFallbackTests(unittest.TestCase):
    def setUp(self):
        self.base = [(str(i), i * 250, 250) for i in range(40)]

    def test_eight_edits_use_safe_full_fallback(self):
        c = PartialGeometryRoutingCache(capacity=1)
        c.route(self.base, 0, recent_routes=8)
        modified = list(self.base)
        for i in range(10, 18):
            modified[i] = (str(i), i * 250 + 5, 250)
        self.assertEqual(c.route(modified, 0, recent_routes=8),
                         scalable_obstacle_routes(modified, 0, recent_routes=8))
        self.assertEqual(c.high_edit_fallbacks, 1)
        self.assertEqual(c.validation_attempts, 0)

    def test_seven_edits_keep_partial_validation_eligible(self):
        c = PartialGeometryRoutingCache(capacity=1)
        c.route(self.base, 0, recent_routes=8)
        modified = list(self.base)
        for i in range(10, 17):
            modified[i] = (str(i), i * 250 + 5, 250)
        self.assertEqual(c.route(modified, 0, recent_routes=8),
                         scalable_obstacle_routes(modified, 0, recent_routes=8))
        self.assertEqual(c.high_edit_fallbacks, 0)

    def test_threshold_is_configurable_per_cache(self):
        a = PartialGeometryRoutingCache()
        b = PartialGeometryRoutingCache()
        a.high_edit_threshold = 4
        self.assertEqual(b.high_edit_threshold, 8)
