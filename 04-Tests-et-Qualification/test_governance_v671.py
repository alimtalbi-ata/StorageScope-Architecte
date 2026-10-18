import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import reconcile_tree_rows
class FakeTree:
 def __init__(self):self.data={};self.selected=();self.scroll=.25
 def get_children(self):return tuple(self.data)
 def selection(self):return self.selected
 def yview(self):return (self.scroll,1.)
 def delete(self,i):self.data.pop(i)
 def insert(self,parent,pos,iid,values):self.data[iid]=values
 def exists(self,i):return i in self.data
 def selection_set(self,ids):self.selected=ids
 def yview_moveto(self,y):self.scroll=y
class TestRebuild(unittest.TestCase):
 def test_rebuild_preserves_selection_and_scroll(self):
  t=FakeTree();t.data={str(i):(i,) for i in range(500)};t.selected=('12',)
  reconcile_tree_rows(t,[(str(i),(i,)) for i in range(500)])
  self.assertEqual(t.selected,('12',));self.assertEqual(t.scroll,.25)
 def test_duplicates_rejected_before_changes(self):
  t=FakeTree()
  with self.assertRaises(ValueError):reconcile_tree_rows(t,[('x',(1,)),('x',(2,))])
  self.assertEqual(t.data,{})
if __name__=='__main__':unittest.main()
