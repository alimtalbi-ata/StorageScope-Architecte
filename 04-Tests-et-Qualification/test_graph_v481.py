import unittest
from graph_layout import scalable_obstacle_routes, route_obstacles

class RoutingV481(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(scalable_obstacle_routes([],300),[])
    def test_stable_and_endpoints(self):
        nodes=[(('ACTION',str(i),'',False),100+i%4*220,140+i//4*80) for i in range(100)]
        routes=scalable_obstacle_routes(nodes,300)
        self.assertEqual(routes,scalable_obstacle_routes(nodes,300))
        self.assertEqual([p[-1] for p in routes],[(x,y-24) for _,x,y in nodes])
    def test_validation(self):
        for n in (-1,257,True,2.3):
            with self.assertRaises(ValueError):scalable_obstacle_routes([],300,recent_routes=n)
    def test_no_cards_crossed_simple(self):
        nodes=[(('ACTION',str(i),'',False),100+i*230,140) for i in range(4)]
        routes=scalable_obstacle_routes(nodes,400)
        rects=[(x-95,y-24,x+95,y+24) for _,x,y in nodes]
        self.assertFalse([(i,j) for i,j in route_obstacles(routes,rects) if i!=j])
    def test_ui_wiring(self):
        from pathlib import Path
        code=(Path(__file__).parent/'desktop.py').read_text()
        self.assertIn('RouteScheduler(scalable_obstacle_routes,self._route_queue.put)',code)
