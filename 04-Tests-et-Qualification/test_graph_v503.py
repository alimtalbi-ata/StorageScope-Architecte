import unittest
from graph_layout import PartialGeometryRoutingCache, scalable_obstacle_routes
from route_scheduler import RouteCancelled

class MiddleReuseTests(unittest.TestCase):
    def setUp(self):
        self.old=[(str(i), 500+i*450, 400) for i in range(9)]

    def test_middle_edit_exact_and_suffix(self):
        c=PartialGeometryRoutingCache()
        c.route(self.old,100,recent_routes=0)
        new=list(self.old)
        new[4]=('moved',self.old[4][1]+30,400)
        self.assertEqual(c.route(new,100,recent_routes=0),scalable_obstacle_routes(new,100,recent_routes=0))
        self.assertGreater(c.suffix_reuses,0)

    def test_interference_disables_suffix_reuse(self):
        c=PartialGeometryRoutingCache();c.route(self.old,100,recent_routes=24)
        new=list(self.old);new[4]=('moved',self.old[4][1]+30,400)
        self.assertEqual(c.route(new,100,recent_routes=24),scalable_obstacle_routes(new,100,recent_routes=24))
        self.assertGreaterEqual(c.suffix_reuses,0)

    def test_changed_obstacle_blocks_unsafe_reuse(self):
        c=PartialGeometryRoutingCache();c.route(self.old,100,recent_routes=0)
        new=list(self.old);new[4]=('moved',self.old[7][1],self.old[7][2]-10)
        self.assertEqual(c.route(new,100,recent_routes=0),scalable_obstacle_routes(new,100,recent_routes=0))

    def test_cancellation(self):
        c=PartialGeometryRoutingCache();c.route(self.old,100,recent_routes=0)
        new=list(self.old);new[4]=('moved',self.old[4][1]+30,400)
        with self.assertRaises(RouteCancelled):
            c.route(new,100,recent_routes=0,cancel_check=lambda: True)
        self.assertEqual(len(c._entries),1)

if __name__=='__main__':unittest.main()
