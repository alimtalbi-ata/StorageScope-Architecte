import unittest
from graph_layout import ObstacleBucketIndex, _fast_route_hits_rect

class ObstacleIndex496(unittest.TestCase):
    def test_overflow_does_not_create_false_collision(self):
        rects=[(-1000000,1000,1000000,1100),(0,0,10,10)]
        idx=ObstacleBucketIndex(rects,64)
        self.assertEqual(idx.query([(5,20),(5,30)]),set())
        self.assertEqual(idx.query([(5,1050),(5,1060)]),{0})
    def test_very_long_path(self):
        rects=[(-100,0,100,20),(900000,0,900010,20)]
        path=[(-1000000,10),(1000000,10)]
        self.assertEqual(ObstacleBucketIndex(rects).query(path),{0,1})
    def test_matches_linear_on_multiple_segments(self):
        rects=[(-1000000,1000,1000000,1100),(10,10,30,30),(40,40,60,60)]
        paths=[[(20,0),(20,50),(50,50)],[(5,5),(5,100)],[(20,1050),(50,1050)]]
        idx=ObstacleBucketIndex(rects)
        for path in paths:
            self.assertEqual(idx.query(path),{i for i,r in enumerate(rects) if _fast_route_hits_rect(path,r)})
