import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import reconcile_tree_rows
from test_governance_v665 import Tree
class TestReconcile(unittest.TestCase):
 def test_reverse(self):
  t=Tree();a=[(str(i),(i,)) for i in range(100)];reconcile_tree_rows(t,a);reconcile_tree_rows(t,list(reversed(a)));self.assertEqual(t.order,[i for i,_ in reversed(a)])
 def test_large_reorder_avoids_moves(self):
  from test_governance_v666 import CountTree
  t=CountTree();a=[(str(i),(i,)) for i in range(100)];reconcile_tree_rows(t,a);reconcile_tree_rows(t,list(reversed(a)));self.assertEqual(t.moves,0)
 def test_noop(self):
  t=Tree();a=[(str(i),(i,)) for i in range(100)];reconcile_tree_rows(t,a);reconcile_tree_rows(t,a);self.assertEqual(len(t.order),100)
 def test_update(self):
  t=Tree();reconcile_tree_rows(t,[('a',('1',))]);reconcile_tree_rows(t,[('a',('2',))]);self.assertEqual(t.rows['a'],('2',))
if __name__=='__main__':unittest.main()
