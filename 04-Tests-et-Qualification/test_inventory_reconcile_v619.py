import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / '03-Sources' / 'inventory_reconcile_v619.py'
spec = importlib.util.spec_from_file_location('inventory_reconcile_v619', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ReconciliationTests(unittest.TestCase):
    def test_same_serial(self):
        result = mod.reconcile([{'source':'a','serial':'ABC','name':'x'}, {'source':'b','serial':'abc','name':'y'}])
        self.assertEqual(result['candidate_count'], 1)
        self.assertEqual(result['candidates'][0]['conflicts'][0]['field'], 'name')
    def test_no_name_only_merge(self):
        self.assertEqual(mod.reconcile([{'source':'a','name':'x'}, {'source':'b','name':'x'}])['candidate_count'], 0)
    def test_different_identifiers(self):
        self.assertEqual(mod.reconcile([{'source':'a','serial':'1'}, {'source':'b','serial':'2'}])['candidate_count'], 0)
    def test_missing_source(self):
        self.assertEqual(len(mod.reconcile([{'serial':'1'}])['invalid_records']), 1)
    def test_non_object(self):
        self.assertEqual(len(mod.reconcile([None])['invalid_records']), 1)
    def test_input_not_modified(self):
        data = [{'source':'a','wwn':'ABC'}, {'source':'b','wwn':'abc'}]
        before = repr(data)
        self.assertEqual(mod.reconcile(data)['automatic_merges'], 0)
        self.assertEqual(repr(data), before)
    def test_bad_top_level(self):
        with self.assertRaises(ValueError): mod.reconcile({})
    def test_duplicate_evidence(self):
        data=[{'source':'a','uuid':'u','serial':'s'}, {'source':'b','uuid':'u','serial':'s'}]
        self.assertEqual(mod.reconcile(data)['candidates'][0]['identity_evidence'], ['serial','uuid'])

if __name__ == '__main__': unittest.main()
