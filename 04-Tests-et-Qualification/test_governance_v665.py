import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import reconcile_tree_rows
class Tree:
 def __init__(self):self.rows={};self.order=[];self.writes=0
 def get_children(self):return tuple(self.order)
 def exists(self,i):return i in self.rows
 def delete(self,i):self.order.remove(i);del self.rows[i]
 def item(self,i,option=None,**kwargs):
  if kwargs:self.rows[i]=tuple(str(v) for v in kwargs['values']);self.writes+=1
  else:return self.rows[i]
 def move(self,i,parent,pos):self.order.remove(i);self.order.insert(pos,i)
 def insert(self,parent,pos,iid,values):self.order.insert(pos,iid);self.rows[iid]=tuple(str(v) for v in values);self.writes+=1
class TestTree(unittest.TestCase):
 def test_first_render(self):
  t=Tree();reconcile_tree_rows(t,[('4',('a','b'))]);self.assertEqual(t.order,['4'])
 def test_unchanged_no_writes(self):
  t=Tree();r=[('1',('a',)),('2',('b',))];reconcile_tree_rows(t,r);reconcile_tree_rows(t,r);self.assertEqual(t.writes,2)
 def test_changed_only(self):
  t=Tree();reconcile_tree_rows(t,[('1',('a',)),('2',('b',))]);reconcile_tree_rows(t,[('1',('a',)),('2',('c',))]);self.assertEqual(t.writes,3)
 def test_delete_and_reorder(self):
  t=Tree();reconcile_tree_rows(t,[('1',('a',)),('2',('b',)),('3',('c',))]);reconcile_tree_rows(t,[('3',('c',)),('1',('a',))]);self.assertEqual(t.order,['3','1']);self.assertNotIn('2',t.rows)
if __name__=='__main__':unittest.main()
