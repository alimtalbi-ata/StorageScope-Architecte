import unittest
from graph_layout import route_interference, optimized_obstacle_routes, route_obstacles

class RoutingV480(unittest.TestCase):
    def test_empty(self):self.assertEqual(optimized_obstacle_routes([],200),[])
    def test_crossing(self):self.assertEqual(route_interference([[(0,5),(10,5)],[(5,0),(5,10)]]),(1,0))
    def test_overlap(self):self.assertEqual(route_interference([[(0,5),(10,5)],[(2,5),(8,5)]]),(0,1))
    def test_touch(self):self.assertEqual(route_interference([[(0,5),(5,5)],[(5,5),(5,10)]]),(0,0))
    def test_determinism(self):
        nodes=[(('ACTION',str(i),'',False),100+(i%3)*220,140+(i//3)*80) for i in range(12)]
        a=optimized_obstacle_routes(nodes,300)
        self.assertEqual(a,optimized_obstacle_routes(nodes,300))
        self.assertEqual(len(a),len(nodes))
        self.assertTrue(all(path[-1]==(x,y-24) for path,(_,x,y) in zip(a,nodes)))
    def test_invalid(self):
        with self.assertRaises(ValueError):optimized_obstacle_routes([(('A',),200,140)],200,clearance=0)
