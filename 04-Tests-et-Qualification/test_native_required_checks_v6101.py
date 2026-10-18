import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('consolidator',ROOT/'02-Compilation-Windows/consolidate-qualification.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class NativeRequiredChecks(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);(self.root/'07-Manifestes').mkdir();(self.root/'07-Manifestes/VERSION').write_text('6.101');base=self.root/'02-Compilation-Windows';base.mkdir();self.base=base
  self.native={'version':'6.101','overall':'PASS','checks':[{'name':n,'status':'PASS'} for n in m.REQUIRED_NATIVE_CHECKS]}
  self.other={'installer':{'version':'6.101','status':'PASS','installed':True,'version_checked':True,'uninstalled':True},'portable':{'version':'6.101','status':'PASS','archive_present':True,'extracted':True,'version_checked':True,'self_test':True,'cleanup':True}}
  self.write()
 def write(self):
  for k,n in m.NAMES.items():(self.base/n).write_text(json.dumps(self.native if k=='native' else self.other[k]))
 def test_complete_pass(self):self.assertEqual(m.consolidate(self.root)['status'],'PASS')
 def test_missing_self_test_rejected(self):
  self.native['checks']=[x for x in self.native['checks'] if x['name']!='executable_self_test'];self.write();self.assertEqual(m.consolidate(self.root)['status'],'FAIL')
 def test_duplicate_name_rejected(self):
  self.native['checks'].append(dict(self.native['checks'][0]));self.write();self.assertEqual(m.consolidate(self.root)['status'],'FAIL')
 def test_failed_check_rejected(self):
  self.native['checks'][0]['status']='FAIL';self.write();self.assertEqual(m.consolidate(self.root)['status'],'FAIL')
 def test_no_installer_evidence_rejected(self):
  self.native['checks']=[x for x in self.native['checks'] if x['name']!='installer_present'];self.write();self.assertEqual(m.consolidate(self.root)['status'],'FAIL')
if __name__=='__main__':unittest.main()
