import unittest
from graph_layout import _fast_route_hits_rect, _fast_interference, route_obstacles, incremental_route_interference, scalable_obstacle_routes

class FastRoutingTests(unittest.TestCase):
    def test_collision_equivalence(self):
        rect=(10,10,30,30)
        for path in [[(0,20),(40,20)],[(20,0),(20,40)],[(0,0),(0,40)],[(10,0),(10,40)],[(0,10),(40,10)],[(0,0),(40,0)]]:
            self.assertEqual(_fast_route_hits_rect(path,rect),bool(route_obstacles([path],[rect])))
    def test_interference_equivalence(self):
        paths=[[(0,0),(0,10),(20,10)],[(5,0),(5,20),(20,20)],[(0,10),(10,10),(10,25)]]
        self.assertEqual(_fast_interference(paths[:2],paths[2]),incremental_route_interference(paths[:2],paths[2]))
    def test_deterministic(self):
        positions=[(('A',str(i)),120+i%3*230,160+i//3*90) for i in range(24)]
        self.assertEqual(scalable_obstacle_routes(positions,350),scalable_obstacle_routes(positions,350))
