import unittest
from graph_viewport import visible_cards,visible_routes
class ViewportTests(unittest.TestCase):
 def test_culls(self):
  nodes=[(('ACTION',str(i),'OPEN',False),100,100+i*100) for i in range(1000)]
  self.assertLess(len(visible_cards(nodes,(0,0,300,300))),10)
 def test_scroll(self):
  nodes=[(('ACTION',str(i),'OPEN',False),100,100+i*100) for i in range(100)]
  self.assertLess(len(visible_cards(nodes,(0,10000,300,10300))),5)
 def test_zoom(self):
  self.assertEqual(len(visible_cards([('x',500,500)],(900,900,1100,1100),2,0)),1)
 def test_routes(self):
  self.assertEqual(len(visible_routes([[(0,0),(10,10)],[(1000,1000),(1200,1200)]],(0,0,100,100))),1)
 def test_invalid(self):
  with self.assertRaises(ValueError):visible_cards([], (0,0,100,100),0)
if __name__=='__main__':unittest.main()
