import unittest
from graph_layout import incremental_route_interference, route_interference, scalable_obstacle_routes

class IncrementalTests(unittest.TestCase):
    def test_equivalence(self):
        prior = [[(0,0),(0,10),(20,10)],[(5,0),(5,15),(25,15)]]
        candidate = [(10,0),(10,20),(30,20)]
        all_cross,all_overlap=route_interference(prior+[candidate])
        old_cross,old_overlap=route_interference(prior)
        self.assertEqual(incremental_route_interference(prior,candidate),(all_cross-old_cross,all_overlap-old_overlap))
    def test_empty(self):
        self.assertEqual(incremental_route_interference([],[(0,0),(1,0)]),(0,0))
    def test_large_deterministic(self):
        nodes=[(('ACTION',str(i),'',False),120+(i%8)*225,140+(i//8)*80) for i in range(40)]
        self.assertEqual(scalable_obstacle_routes(nodes,900),scalable_obstacle_routes(nodes,900))
