import unittest
from graph_layout import RoutingResultCache, scalable_obstacle_routes
from route_scheduler import RouteCancelled

class RoutingResultCacheTests(unittest.TestCase):
    def setUp(self):
        self.p=[(str(i), (i%9)*220, 160+(i//9)*90) for i in range(90)]
    def test_cache_hit_and_copy_isolation(self):
        cache=RoutingResultCache()
        a=cache.route(self.p,110)
        a[0].append(('corrupt','point'))
        b=cache.route(self.p,110)
        self.assertEqual(b,scalable_obstacle_routes(self.p,110))
        self.assertEqual((cache.hits,cache.misses),(1,1))
    def test_coordinate_and_options_invalidate(self):
        cache=RoutingResultCache()
        original=cache.route(self.p,110)
        altered=list(self.p); altered[0]=(altered[0][0],altered[0][1]+30,altered[0][2])
        self.assertEqual(cache.route(altered,110),scalable_obstacle_routes(altered,110))
        self.assertEqual(cache.route(self.p,110,recent_routes=0),scalable_obstacle_routes(self.p,110,recent_routes=0))
        self.assertEqual(cache.misses,3)
        self.assertEqual(cache.route(self.p,110),original)
        self.assertEqual(cache.hits,1)
    def test_lru_eviction(self):
        cache=RoutingResultCache(capacity=2)
        for x in (100,200,100,300,200):cache.route(self.p,x)
        self.assertEqual((cache.hits,cache.misses),(1,4))
        self.assertEqual(len(cache._entries),2)
    def test_cancelled_hit_and_miss(self):
        cache=RoutingResultCache()
        with self.assertRaises(RouteCancelled):cache.route(self.p,110,cancel_check=lambda:True)
        self.assertEqual(len(cache._entries),0)
        cache.route(self.p,110)
        with self.assertRaises(RouteCancelled):cache.route(self.p,110,cancel_check=lambda:True)
        self.assertEqual(cache.hits,0)
    def test_reject_unhashable_and_capacity(self):
        with self.assertRaises(ValueError):RoutingResultCache(0)
        with self.assertRaises(ValueError):RoutingResultCache().route([({'x':1},100,160)],110)
