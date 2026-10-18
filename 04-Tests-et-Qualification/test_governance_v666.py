import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import reconcile_tree_rows
from test_governance_v665 import Tree
class CountTree(Tree):
 def __init__(self):super().__init__();self.moves=0
 def move(self,i,parent,pos):self.moves+=1;super().move(i,parent,pos)
class Tests(unittest.TestCase):
 def test_unchanged_has_zero_moves(self):
  t=CountTree();r=[(str(i),(str(i),)) for i in range(100)];reconcile_tree_rows(t,r);reconcile_tree_rows(t,r);self.assertEqual(t.moves,0)
 def test_one_swap(self):
  t=CountTree();r=[(str(i),(str(i),)) for i in range(10)];reconcile_tree_rows(t,r);r[3],r[4]=r[4],r[3];reconcile_tree_rows(t,r);self.assertEqual(t.order,[x[0] for x in r]);self.assertEqual(t.moves,1)
 def test_page_replacement(self):
  t=CountTree();reconcile_tree_rows(t,[('a',('a',)),('b',('b',))]);reconcile_tree_rows(t,[('c',('c',)),('d',('d',))]);self.assertEqual(t.order,['c','d'])
 def test_value_change_no_move(self):
  t=CountTree();reconcile_tree_rows(t,[('a',('old',))]);reconcile_tree_rows(t,[('a',('new',))]);self.assertEqual(t.moves,0);self.assertEqual(t.rows['a'],('new',))
if __name__=='__main__':unittest.main()
