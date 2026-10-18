import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes
from route_scheduler import RouteCancelled

class PartialTests(unittest.TestCase):
    def test_safe_suffix_reuse(self):
        positions=[(str(i),i*300+200,400) for i in range(8)]
        c=PartialGeometryRoutingCache()
        c.route(positions,100)
        updated=positions+ [('last',10000,400)]
        self.assertEqual(c.route(updated,100),scalable_obstacle_routes(updated,100))
        self.assertEqual(c.partial_reuses,1)
    def test_unsafe_global_lanes_fallback(self):
        positions=[(str(i),i*230,140) for i in range(10)]
        c=PartialGeometryRoutingCache()
        c.route(positions,100)
        changed=positions+[('new',3000,140)]
        self.assertEqual(c.route(changed,100),scalable_obstacle_routes(changed,100))
    def test_modified_middle_and_removed_nodes(self):
        positions=[(str(i),i*240,160) for i in range(9)]
        c=PartialGeometryRoutingCache();c.route(positions,100)
        for modified in (positions[:5]+[('changed',1600,160)]+positions[6:],positions[:6]):
            self.assertEqual(c.route(modified,100),scalable_obstacle_routes(modified,100))
    def test_cancel_does_not_store(self):
        c=PartialGeometryRoutingCache()
        with self.assertRaises(RouteCancelled):c.route([('a',200,160)],100,cancel_check=lambda:True)
        self.assertFalse(c._entries)
    def test_metadata_and_copy(self):
        c=PartialGeometryRoutingCache();a=c.route([({'x':1},200,160)],100)
        a[0].append((999,999))
        self.assertEqual(c.route([({'x':2},200,160)],100),scalable_obstacle_routes([(0,200,160)],100))
if __name__=='__main__':unittest.main()
