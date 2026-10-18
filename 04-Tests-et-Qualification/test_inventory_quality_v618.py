import datetime as dt,importlib.util,pathlib,unittest
P=pathlib.Path(__file__).resolve().parents[1]/"03-Sources/inventory_quality_v618.py"
s=importlib.util.spec_from_file_location("inventory_quality_v618",P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
NOW=dt.datetime(2026,10,17,tzinfo=dt.timezone.utc)
class QualityTests(unittest.TestCase):
 def check(self,rows):return m.inspect_inventory(rows,now=NOW)
 def test_empty(self):self.assertEqual(self.check([])["score"],100)
 def test_clean(self):self.assertEqual(self.check([{"id":"1","name":"a","type":"server"}])["issue_count"],0)
 def test_duplicate(self):self.assertIn("duplicate_id",self.check([{"id":"1","name":"a","type":"s"},{"id":"1","name":"b","type":"s"}])["counts"])
 def test_required(self):self.assertEqual(self.check([{}])["counts"]["missing_field"],3)
 def test_invalid_record(self):self.assertIn("invalid_record",self.check([None])["counts"])
 def test_stale(self):self.assertIn("stale_record",self.check([{"id":"1","name":"a","type":"s","updated_at":"2020-01-01T00:00:00Z"}])["counts"])
 def test_future(self):self.assertIn("future_timestamp",self.check([{"id":"1","name":"a","type":"s","updated_at":"2027-01-01T00:00:00Z"}])["counts"])
 def test_invalid_time(self):self.assertIn("invalid_timestamp",self.check([{"id":"1","name":"a","type":"s","updated_at":"bad"}])["counts"])
 def test_timezone(self):self.assertIn("invalid_timestamp",self.check([{"id":"1","name":"a","type":"s","updated_at":"2026-10-17T00:00:00"}])["counts"])
 def test_nondestructive(self):
  rows=[{"id":"x","name":"A","type":"s"}];before=repr(rows);self.check(rows);self.assertEqual(repr(rows),before)
if __name__=="__main__":unittest.main()
