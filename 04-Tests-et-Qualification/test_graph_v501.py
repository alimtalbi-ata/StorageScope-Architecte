import unittest
from graph_layout import GeometryRoutingCache, scalable_obstacle_routes
from route_scheduler import RouteCancelled

class GeometryCacheTests(unittest.TestCase):
    def setUp(self):
        self.positions=[({'label':str(i),'status':'open'},(i%7)*230,170+(i//7)*85) for i in range(49)]
    def test_metadata_only_update_reuses_routes(self):
        cache=GeometryRoutingCache()
        first=cache.route(self.positions,110)
        modified=[({'label':'new'+str(i),'status':'closed'},x,y) for i,(_,x,y) in enumerate(self.positions)]
        self.assertEqual(cache.route(modified,110),first)
        self.assertEqual(first,scalable_obstacle_routes(self.positions,110))
        self.assertEqual((cache.hits,cache.misses),(1,1))
    def test_geometry_order_and_options_invalidate(self):
        c=GeometryRoutingCache()
        c.route(self.positions,110)
        moved=list(self.positions); n,x,y=moved[0]; moved[0]=(n,x+1,y)
        self.assertEqual(c.route(moved,110),scalable_obstacle_routes(moved,110))
        swapped=list(self.positions);swapped[0],swapped[1]=swapped[1],swapped[0]
        c.route(swapped,110);c.route(self.positions,110,recent_routes=0)
        self.assertEqual(c.misses,4)
    def test_no_mutable_aliasing(self):
        c=GeometryRoutingCache();a=c.route(self.positions,110);a[0].append(('bad','point'))
        self.assertNotIn(('bad','point'),c.route(self.positions,110)[0])
    def test_cancellation_on_hit_and_miss(self):
        c=GeometryRoutingCache()
        with self.assertRaises(RouteCancelled):c.route(self.positions,110,cancel_check=lambda:True)
        c.route(self.positions,110)
        with self.assertRaises(RouteCancelled):c.route(self.positions,110,cancel_check=lambda:True)
        self.assertEqual(c.hits,0)
    def test_lru_capacity_and_invalid_geometry(self):
        c=GeometryRoutingCache(capacity=2)
        for root in (110,120,110,130,120):c.route(self.positions,root)
        self.assertEqual((c.hits,c.misses,len(c._entries)),(1,4,2))
        with self.assertRaises(ValueError):c.route([('a',[],200)],110)

if __name__=='__main__':unittest.main()
