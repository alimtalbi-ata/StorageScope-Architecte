import unittest, tempfile, pathlib, json, importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('consolidator',ROOT/'02-Compilation-Windows/consolidate-qualification.py')
MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)
class QualificationV699(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=pathlib.Path(self.tmp.name);(self.root/'07-Manifestes').mkdir();(self.root/'07-Manifestes/VERSION').write_text('6.99')
  self.base=self.root/'02-Compilation-Windows';self.base.mkdir()
  self.native={'version':'6.99','overall':'PASS','checks':[{'name':name,'status':'PASS'} for name in MOD.REQUIRED_NATIVE_CHECKS]}
  self.installer={'version':'6.99','status':'PASS','installed':True,'version_checked':True,'uninstalled':True}
  self.portable={'version':'6.99','status':'PASS','archive_present':True,'extracted':True,'version_checked':True,'self_test':True,'cleanup':True}
  self.save()
 def save(self):
  for k,v in [('native',self.native),('installer',self.installer),('portable',self.portable)]:
   (self.base/MOD.NAMES[k]).write_text(json.dumps(v))
 def test_real_native_schema_passes(self):self.assertEqual(MOD.consolidate(self.root)['status'],'PASS')
 def test_native_failed_check_rejected(self):
  self.native['checks'][0]['status']='FAIL';self.save();self.assertEqual(MOD.consolidate(self.root)['status'],'FAIL')
 def test_missing_required_native_check_rejected(self):
  self.native['checks'].pop();self.save();self.assertEqual(MOD.consolidate(self.root)['status'],'FAIL')
 def test_empty_native_checks_rejected(self):
  self.native['checks']=[];self.save();self.assertEqual(MOD.consolidate(self.root)['status'],'FAIL')
 def test_missing_version_rejected(self):
  del self.installer['version'];self.save();self.assertEqual(MOD.consolidate(self.root)['status'],'FAIL')
 def test_missing_native_report_rejected(self):
  (self.base/MOD.NAMES['native']).unlink();self.assertEqual(MOD.consolidate(self.root)['status'],'FAIL')
if __name__=='__main__':unittest.main()
