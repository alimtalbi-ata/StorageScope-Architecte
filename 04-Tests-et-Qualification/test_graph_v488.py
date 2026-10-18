import unittest
from graph_spatial import card_index, route_index, SpatialIndex
from graph_viewport import visible_cards, visible_routes

class SpatialTests(unittest.TestCase):
    def setUp(self):
        self.cards=[(('ACTION',str(i),'OPEN',False),i%30*220,i//30*90) for i in range(1500)]
        self.routes=[[(i%30*220,0),(i%30*220,i//30*90)] for i in range(1500)]
    def test_card_equivalence(self):
        idx=card_index(self.cards)
        for zoom in (0.5,1,2):
            for bounds in ((0,0,800,600),(1000,900,1700,1500),(4000,2000,5000,3000)):
                self.assertEqual(idx.query(bounds,zoom),visible_cards(self.cards,bounds,zoom))
    def test_route_equivalence(self):
        idx=route_index(self.routes)
        for zoom in (0.5,1,2):
            bounds=(500,500,1200,1100)
            self.assertEqual(idx.query(bounds,zoom),visible_routes(self.routes,bounds,zoom))
    def test_invalid_cell(self):
        with self.assertRaises(ValueError):SpatialIndex([],lambda _: (0,0,1,1),0)
    def test_negative_coordinates(self):
        idx=card_index([(('A','1','OPEN',False),-300,-300)])
        self.assertEqual(len(idx.query((-400,-400,-200,-200),1,0)),1)
    def test_empty(self):
        self.assertEqual(route_index([]).query((0,0,100,100)),[])
if __name__=='__main__':unittest.main()
