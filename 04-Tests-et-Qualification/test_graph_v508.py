import random
import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes


class MultiEditDeltaTests(unittest.TestCase):
    def test_distant_multiple_edits_reuse_prefix(self):
        old = [(str(i), 260 + i * 250, 180 + (i % 3) * 110) for i in range(18)]
        new = list(old)
        for j in (11, 15, 17):
            name, x, y = new[j]
            new[j] = (name, x + 13, y + 17)
        cache = PartialGeometryRoutingCache()
        cache.route(old, 0, recent_routes=0)
        actual = cache.route(new, 0, recent_routes=0)
        self.assertEqual(actual, scalable_obstacle_routes(new, 0, recent_routes=0))
        self.assertEqual(cache.validation_delta_rectangles, 6)
        self.assertGreater(cache.partial_reuses, 0)

    def test_random_multi_edit_equivalence(self):
        rng = random.Random(508)
        for recent in (0, 3, 24):
            for _ in range(35):
                old = [(str(i), 260 + i * 220, 170 + rng.randrange(5) * 85) for i in range(16)]
                new = list(old)
                for j in rng.sample(range(3, 16), rng.randrange(2, 6)):
                    name, x, y = new[j]
                    new[j] = (name, x + rng.randrange(-20, 21), y + rng.randrange(-20, 21))
                cache = PartialGeometryRoutingCache()
                cache.route(old, 0, recent_routes=recent)
                self.assertEqual(cache.route(new, 0, recent_routes=recent),
                                 scalable_obstacle_routes(new, 0, recent_routes=recent))

    def test_budget_uses_changed_not_unchanged_suffix(self):
        old = [(str(i), 300 + i * 260, 160 + i % 2 * 100) for i in range(80)]
        new = list(old)
        for j in (65, 78):
            name, x, y = new[j]
            new[j] = (name, x + 12, y + 12)
        cache = PartialGeometryRoutingCache()
        cache.route(old, 0, recent_routes=0)
        cache.route(new, 0, recent_routes=0)
        self.assertEqual(cache.validation_delta_rectangles, 4)
        self.assertLess(cache.validation_last_estimate, 12000)
