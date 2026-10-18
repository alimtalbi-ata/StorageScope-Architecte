import unittest
from windows_home_v570 import home_cards

class HomePriorityV601(unittest.TestCase):
    def test_frequent_actions_first(self):
        self.assertEqual([x['page'] for x in home_cards()[:2]], ['Gouvernance','Campagnes'])
    def test_support_actions_second(self):
        self.assertEqual([x['page'] for x in home_cards()[2:]], ['Diagnostic','Maintenance'])
    def test_action_labels_are_specific(self):
        self.assertEqual(len({x['action'] for x in home_cards()}), 4)
        self.assertTrue(all(len(x['action']) > 10 for x in home_cards()))
    def test_grouping(self):
        self.assertEqual([x['group'] for x in home_cards()], ['quotidien']*2+['support']*2)
    def test_home_wires_action_label(self):
        from pathlib import Path
        source=(Path(__file__).parent/'storagescope_windows.py').read_text(encoding='utf-8')
        self.assertIn("text=card['action']",source)
