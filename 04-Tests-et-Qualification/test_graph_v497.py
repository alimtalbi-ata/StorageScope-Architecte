import random
import unittest
from graph_layout import RecentSegmentIndex, _route_segments, scalable_obstacle_routes

class IncrementalIndexTests(unittest.TestCase):
    def test_duplicate_segments_and_removal(self):
        a=_route_segments([(0,0),(0,10),(20,10)])
        b=_route_segments([(0,0),(0,10),(30,10)])
        idx=RecentSegmentIndex(())
        idx.append(a);idx.append(a);idx.append(b)
        probe=[(0,5),(10,5),(10,10)]
        self.assertEqual(idx.score(probe), RecentSegmentIndex([a,a,b]).score(probe))
        idx.discard(a)
        self.assertEqual(idx.score(probe), RecentSegmentIndex([a,b]).score(probe))
        idx.discard(a);idx.discard(b)
        self.assertEqual(idx.score(probe), (0,0))

    def test_randomized_rolling_window(self):
        rng=random.Random(497)
        idx=RecentSegmentIndex(())
        recent=[]
        for _ in range(150):
            x=rng.randrange(0,10)*10;y=rng.randrange(0,10)*10
            seg=_route_segments([(x,0),(x,y),(100,y)])
            idx.append(seg);recent.append(seg)
            if len(recent)>24:
                idx.discard(recent.pop(0))
            candidate=[(rng.randrange(0,10)*10,0),(rng.randrange(0,10)*10,100)]
            self.assertEqual(idx.score(candidate),RecentSegmentIndex(recent).score(candidate))

    def test_router_determinism_and_cancel(self):
        positions=[(str(i), (i%17)*230, 180+(i//17)*90) for i in range(80)]
        a=scalable_obstacle_routes(positions,120)
        self.assertEqual(a,scalable_obstacle_routes(positions,120))
        self.assertEqual(len(a),80)
        from route_scheduler import RouteCancelled
        with self.assertRaises(RouteCancelled):
            scalable_obstacle_routes(positions,120,cancel_check=lambda:True)
