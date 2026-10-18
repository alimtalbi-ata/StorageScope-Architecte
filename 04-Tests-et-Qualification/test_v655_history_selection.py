import sys,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import history_for_selection
class HistorySelectionTests(unittest.TestCase):
 def test_selected_key_exact(self):
  with patch('governance_desktop.read_audit_history',return_value=[]) as fn:
   self.assertEqual(history_for_selection('registry.sqlite','key:long-identifier'),[])
   fn.assert_called_once_with('registry.sqlite',limit=100,candidate='key:long-identifier')
 def test_all_without_selection(self):
  with patch('governance_desktop.read_audit_history',return_value=[{'seq':1}]) as fn:
   self.assertEqual(len(history_for_selection('registry.sqlite')),1)
   fn.assert_called_once_with('registry.sqlite',limit=100,candidate=None)
 def test_reject_empty_key(self):
  for key in ('', '   ', 12):
   with self.subTest(key=key),self.assertRaises(ValueError):history_for_selection('x',key)
 def test_limit_forwarded(self):
  with patch('governance_desktop.read_audit_history',return_value=[]) as fn:
   history_for_selection('x','key',limit=25)
   self.assertEqual(fn.call_args.kwargs['limit'],25)
if __name__=='__main__':unittest.main()
