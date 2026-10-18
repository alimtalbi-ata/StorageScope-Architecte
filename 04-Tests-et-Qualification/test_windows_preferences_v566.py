"""Functional preference tests. Author: Abdelhalim Talbi."""
import json
import tempfile
import unittest
from pathlib import Path
from windows_preferences_v566 import DEFAULTS, load_preferences, save_preferences, validate_preferences

class PreferencesTests(unittest.TestCase):
    def test_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_preferences(Path(d)/'missing.json'), DEFAULTS)
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'
            save_preferences(p, {'geometry':'1280x800','last_page':'Campagnes'})
            self.assertEqual(load_preferences(p)['last_page'],'Campagnes')
            self.assertEqual(load_preferences(p)['geometry'],'1280x800')
    def test_invalid_page(self):
        with self.assertRaises(ValueError): validate_preferences({'last_page':'../../x'})
    def test_invalid_geometry(self):
        with self.assertRaises(ValueError): validate_preferences({'geometry':'100x100'})
    def test_invalid_theme(self):
        with self.assertRaises(ValueError): validate_preferences({'theme':'evil'})
    def test_corrupted_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'; p.write_text('{')
            with self.assertRaises(json.JSONDecodeError): load_preferences(p)
    def test_atomic_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'; save_preferences(p, {})
            self.assertEqual([x.name for x in Path(d).iterdir()], ['prefs.json'])
    def test_invalid_save_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'; save_preferences(p, {})
            original=p.read_bytes()
            with self.assertRaises(ValueError): save_preferences(p, {'geometry':'bad'})
            self.assertEqual(p.read_bytes(), original)
