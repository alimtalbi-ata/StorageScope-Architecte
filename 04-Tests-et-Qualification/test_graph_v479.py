import unittest
from graph_layout import obstacle_aware_routes,route_obstacles

class ObstacleAwareTests(unittest.TestCase):
    def test_multiline_column_avoids_cards(self):
        p=[(('ACTION',str(i),'OPEN',False),110,140+i*80) for i in range(5)]
        routes=obstacle_aware_routes(p,250)
        rects=[(x-95,y-24,x+95,y+24) for _,x,y in p]
        self.assertEqual([(i,j) for i,j in route_obstacles(routes,rects) if i!=j],[])
    def test_destination(self):
        p=[(('ADR','a','OPEN',False),110,140)]
        self.assertEqual(obstacle_aware_routes(p,250)[0][-1],(110,116))
    def test_repeatable(self):
        p=[(('ADR','a','OPEN',False),110,140)]
        self.assertEqual(obstacle_aware_routes(p,250),obstacle_aware_routes(p,250))
    def test_empty(self):
        self.assertEqual(obstacle_aware_routes([],250),[])
    def test_bad_clearance(self):
        with self.assertRaises(ValueError):obstacle_aware_routes([],250,clearance=0)
    def test_ui_wired(self):
        from pathlib import Path
        s=(Path(__file__).parent/'desktop.py').read_text()
        self.assertIn('RouteScheduler(scalable_obstacle_routes,self._route_queue.put)',s)
