import json
import tempfile
import unittest
from pathlib import Path
from decision_views_v543 import SavedViews, validate_filters

FILTERS={'query':'SAN','owner':'Alice','status':'OPEN','deadline':'all'}
class SavedViewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'views.json'
        self.views=SavedViews(self.path)
    def test_empty(self):self.assertEqual(self.views.load(),{})
    def test_roundtrip(self):
        self.views.save('Vue SAN',FILTERS)
        self.assertEqual(self.views.load()['Vue SAN'],FILTERS)
    def test_overwrite(self):
        self.views.save('A',FILTERS)
        self.views.save('A',{**FILTERS,'query':'NAS'})
        self.assertEqual(self.views.load()['A']['query'],'NAS')
    def test_delete(self):
        self.views.save('A',FILTERS);self.views.delete('A')
        self.assertEqual(self.views.load(),{})
    def test_delete_missing(self):
        with self.assertRaises(KeyError):self.views.delete('X')
    def test_bad_name(self):
        with self.assertRaises(ValueError):self.views.save('../\n',FILTERS)
    def test_bad_filter(self):
        with self.assertRaises(ValueError):self.views.save('A',{**FILTERS,'status':'SUPERUSER'})
    def test_bad_query(self):
        with self.assertRaises(ValueError):validate_filters({**FILTERS,'query':'x'*257})
    def test_bad_schema(self):
        self.path.write_text('{"schema":"unknown","views":{}}')
        with self.assertRaises(ValueError):self.views.load()
    def test_corrupt_no_overwrite(self):
        self.path.write_text('broken')
        with self.assertRaises(ValueError):self.views.save('A',FILTERS)
        self.assertEqual(self.path.read_text(),'broken')
    def test_too_many(self):
        for i in range(32):self.views.save(str(i),FILTERS)
        with self.assertRaises(ValueError):self.views.save('extra',FILTERS)
    def test_size_limit(self):
        self.path.write_bytes(b' '*65537)
        with self.assertRaises(ValueError):self.views.load()
if __name__=='__main__':unittest.main()
