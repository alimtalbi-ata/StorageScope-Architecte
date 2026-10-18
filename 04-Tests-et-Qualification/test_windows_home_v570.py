"""Home dashboard model regression tests."""
import unittest
from windows_home_v570 import home_cards, health_summary

class HomeV570Tests(unittest.TestCase):
    def test_cards_unique_and_actionable(self):
        cards = home_cards()
        self.assertEqual(len(cards), 4)
        self.assertEqual({c['page'] for c in cards}, {'Gouvernance','Campagnes','Diagnostic','Maintenance'})
        self.assertTrue(all(c['title'] and c['description'] for c in cards))
    def test_all_healthy(self):
        self.assertEqual(health_summary({'decisions':'OK','campaigns':'OK'}),'2 bases vérifiées')
    def test_missing_is_not_healthy(self):
        self.assertIn('aucune base',health_summary({'decisions':'ABSENTE','campaigns':'ABSENTE'}))
    def test_partial(self):
        self.assertIn('partiellement',health_summary({'decisions':'OK','campaigns':'ABSENTE'}))
    def test_error(self):
        self.assertIn('Anomalie',health_summary({'decisions':'ERREUR: corruption','campaigns':'OK'}))
    def test_missing_key(self):
        with self.assertRaises(ValueError): health_summary({'decisions':'OK'})
    def test_unknown_state(self):
        self.assertIn('inconnu',health_summary({'decisions':'UNKNOWN','campaigns':'OK'}))

if __name__ == '__main__': unittest.main()
