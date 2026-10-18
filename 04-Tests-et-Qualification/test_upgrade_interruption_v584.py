import tempfile
import unittest
from pathlib import Path
from upgrade_interruption_v584 import rehearse

class InterruptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir()
        (self.data/'governance-views.json').write_text('{"example":true}',encoding='utf-8')
    def test_interrupted_restore_and_recovery(self):
        result=rehearse(self.data,self.root/'backups')
        self.assertTrue(result['passed']);self.assertTrue(result['live_data_unchanged'])
    def test_missing_data_refused(self):
        with self.assertRaises(ValueError):rehearse(self.root/'missing',self.root/'backups')
    def test_no_supported_data_refused(self):
        (self.data/'governance-views.json').unlink()
        with self.assertRaises(ValueError):rehearse(self.data,self.root/'backups')
    def test_existing_data_preserved(self):
        p=self.data/'governance-views.json';original=p.read_bytes()
        rehearse(self.data,self.root/'backups')
        self.assertEqual(p.read_bytes(),original)
    def test_second_rehearsal_unique_snapshot(self):
        first=rehearse(self.data,self.root/'backups')
        second=rehearse(self.data,self.root/'backups')
        self.assertNotEqual(first['snapshot'],second['snapshot'])
