import unittest
from test_governance_v665 import Tree
from governance_desktop import reconcile_tree_rows
class StateTree(Tree):
 def __init__(self):super().__init__();self.selected=();self.scroll=.4
 def selection(self):return self.selected
 def selection_set(self,items):self.selected=tuple(items)
 def yview(self):return (self.scroll,min(1,self.scroll+.2))
 def yview_moveto(self,x):self.scroll=x
class Tests(unittest.TestCase):
 def test_mass_update_preserves_selection_and_scroll(self):
  t=StateTree();a=[(str(i),('a',)) for i in range(100)];reconcile_tree_rows(t,a);t.selected=('25',)
  reconcile_tree_rows(t,[(str(i),('b',)) for i in range(100)])
  self.assertEqual(t.selected,('25',));self.assertEqual(t.scroll,.4);self.assertEqual(t.rows['25'],('b',))
 def test_reverse_preserves_selection(self):
  t=StateTree();a=[(str(i),('a',)) for i in range(100)];reconcile_tree_rows(t,a);t.selected=('25',)
  reconcile_tree_rows(t,list(reversed(a)));self.assertEqual(t.selected,('25',));self.assertEqual(t.scroll,.4)
 def test_small_update_incremental(self):
  t=StateTree();a=[(str(i),('a',)) for i in range(100)];reconcile_tree_rows(t,a);writes=t.writes
  reconcile_tree_rows(t,[(str(i),('b' if i==4 else 'a',)) for i in range(100)]);self.assertEqual(t.writes,writes+1)
if __name__=='__main__':unittest.main()
