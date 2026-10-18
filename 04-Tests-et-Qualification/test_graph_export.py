import tempfile,unittest
from pathlib import Path
from graph_export import export_svg,export_png
class ExportTests(unittest.TestCase):
 def test_svg_escaped(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'graph.svg';export_svg({'title':'A < B & C','nodes':[('ACTION','<script>','OPEN',True)]},p)
   s=p.read_text();self.assertIn('&lt;script&gt;',s);self.assertNotIn('<script>',s);self.assertIn('A &lt; B &amp; C',s)
 def test_png(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'graph.png';export_png({'title':'Test','nodes':[('ADR','1','DONE',False)]},p)
   self.assertEqual(p.read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
 def test_empty(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'empty.svg';export_svg({'nodes':[]},p);self.assertIn('<svg',p.read_text())
 def test_invalid(self):
  with self.assertRaises(ValueError):export_svg({'nodes':'bad'},'unused.svg')
