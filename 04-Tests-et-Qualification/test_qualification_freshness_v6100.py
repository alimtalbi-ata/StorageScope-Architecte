import importlib.util,json,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('qualification',ROOT/'02-Compilation-Windows/consolidate-qualification.py')
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)
class FreshnessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/'07-Manifestes').mkdir();(self.root/'07-Manifestes/VERSION').write_text('6.100');self.base=self.root/'02-Compilation-Windows';self.base.mkdir()
  data={'native':{'version':'6.100','overall':'PASS','checks':[{'status':'PASS'}]},'installer':{'version':'6.100','status':'PASS','installed':True,'version_checked':True,'uninstalled':True},'portable':{'version':'6.100','status':'PASS','archive_present':True,'extracted':True,'version_checked':True,'self_test':True,'cleanup':True}}
  for k,n in mod.NAMES.items():(self.base/n).write_text(json.dumps(data[k]))
 def test_valid_fresh(self):self.assertEqual(mod.consolidate(self.root,time.time()-10)['status'],'PASS')
 def test_old_reports_rejected(self):self.assertEqual(mod.consolidate(self.root,time.time()+10)['status'],'FAIL')
 def test_missing_report_rejected(self):(self.base/mod.NAMES['native']).unlink();self.assertEqual(mod.consolidate(self.root)['status'],'FAIL')
 def test_wrong_version_rejected(self):
  p=self.base/mod.NAMES['portable'];d=json.loads(p.read_text());d['version']='6.99';p.write_text(json.dumps(d));self.assertEqual(mod.consolidate(self.root)['status'],'FAIL')
 def test_workflow_clears_stale_evidence(self):
  t=(ROOT/'.github/workflows/windows-build.yml').read_text();self.assertIn('Remove stale qualification evidence',t);self.assertIn('--min-timestamp',t)
if __name__=='__main__':unittest.main()
