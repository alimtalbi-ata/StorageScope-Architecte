import unittest
from test_governance_v668 import StateTree
from governance_desktop import reconcile_tree_rows

class Tests(unittest.TestCase):
    def test_large_page_preserves_selection_and_scroll(self):
        t=StateTree(); rows=[(str(i),(str(i),)) for i in range(1000)]
        reconcile_tree_rows(t,rows);t.selected=('777',);t.scroll=.3
        reconcile_tree_rows(t,[(str(i),('new',)) for i in range(1000)])
        self.assertEqual(t.selected,('777',));self.assertEqual(t.scroll,.3)
        self.assertEqual(t.rows['777'],('new',))
    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):reconcile_tree_rows(StateTree(),[('x',('a',)),('x',('b',))])
    def test_large_reorder(self):
        t=StateTree(); rows=[(str(i),('a',)) for i in range(1000)]
        reconcile_tree_rows(t,rows);reconcile_tree_rows(t,list(reversed(rows)))
        self.assertEqual(list(t.rows)[0],'999')
if __name__=='__main__':unittest.main()
