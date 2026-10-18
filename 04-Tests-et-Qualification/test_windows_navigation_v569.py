import unittest
from windows_navigation_v569 import route
class NavigationTests(unittest.TestCase):
 def test_accent(self): self.assertEqual(route('décision'),'Gouvernance')
 def test_alias(self): self.assertEqual(route('benchmark'),'Campagnes')
 def test_prefix(self): self.assertEqual(route('maint'),'Maintenance')
 def test_unknown(self): self.assertIsNone(route('zzz'))
 def test_empty(self): self.assertIsNone(route('  '))
 def test_type(self):
  with self.assertRaises(TypeError): route(None)
