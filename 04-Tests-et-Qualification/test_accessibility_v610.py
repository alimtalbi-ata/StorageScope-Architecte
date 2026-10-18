import unittest
from windows_accessibility_v610 import display_metrics
class DisplayMetricsTests(unittest.TestCase):
 def test_compact_1024(self): self.assertEqual(display_metrics(1024,768)['content_padding'],10)
 def test_compact_height(self): self.assertTrue(display_metrics(1920,600)['compact'])
 def test_regular(self): self.assertEqual(display_metrics(1920,1080)['rowheight'],29)
 def test_minimum(self): self.assertEqual(display_metrics(640,480)['rowheight'],26)
 def test_invalid(self):
  with self.assertRaises(ValueError): display_metrics(0,1080)
 def test_bool(self):
  with self.assertRaises(ValueError): display_metrics(True,1080)
