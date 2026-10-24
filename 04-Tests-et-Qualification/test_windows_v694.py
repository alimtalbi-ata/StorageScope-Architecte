import importlib.util, json, pathlib, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('qualify', ROOT/'02-Compilation-Windows/consolidate-qualification.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class ReleaseQualification(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name)
  (self.root/'07-Manifestes').mkdir();(self.root/'07-Manifestes/VERSION').write_text('6.94')
  (self.root/'02-Compilation-Windows').mkdir()
 def report(self,name,obj):
  (self.root/'02-Compilation-Windows'/mod.NAMES[name]).write_text(json.dumps(obj))
 def test_missing_is_failure(self):self.assertEqual(mod.consolidate(self.root)['status'],'FAIL')
 def test_complete_success(self):
  self.report('native',{'overall':'PASS','version':'6.94','checks':[{'name':name,'status':'PASS'} for name in mod.REQUIRED_NATIVE_CHECKS]})
  self.report('installer',{'status':'PASS','version':'6.94','installed':True,'version_checked':True,'uninstalled':True})
  self.report('portable',{'status':'PASS','version':'6.94','archive_present':True,'extracted':True,'version_checked':True,'self_test':True,'cleanup':True})
  self.assertEqual(mod.consolidate(self.root)['status'],'PASS')
 def test_missing_portable_proof_fails(self):
  self.report('native',{'status':'PASS','version':'6.94'})
  self.report('installer',{'status':'PASS','version':'6.94','installed':True,'version_checked':True,'uninstalled':True})
  self.report('portable',{'status':'PASS','version':'6.94','self_test':True,'cleanup':True})
  self.assertEqual(mod.consolidate(self.root)['qualification']['portable']['status'],'FAIL')
 def test_bad_version_fails(self):
  self.report('native',{'status':'PASS','version':'6.93'})
  self.assertEqual(mod.consolidate(self.root)['qualification']['native']['status'],'FAIL')
 def test_workflow_no_multiline_report_path(self):
  s=(ROOT/'.github/workflows/windows-build.yml').read_text()
  self.assertIn("$reportPath = '02-Compilation-Windows/windows-installer-smoke-report.json'",s)
  self.assertIn('consolidate-qualification.py',s)
if __name__=='__main__':unittest.main()
