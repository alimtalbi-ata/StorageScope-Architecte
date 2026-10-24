import tempfile
import unittest
from pathlib import Path
from windows_module_inventory import reachable_modules

ROOT = Path(__file__).resolve().parent

class WindowsPortable589(unittest.TestCase):
    def test_import_closure_excludes_unrelated_scripts(self):
        modules = reachable_modules(ROOT)
        self.assertIn('decision_governance_v537', modules)
        self.assertNotIn('benchmark_v523', modules)
        self.assertNotIn('windows_module_inventory', modules)

    def test_recursive_imports_and_cycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/'main.py').write_text('import a\n')
            (p/'a.py').write_text('import b\n')
            (p/'b.py').write_text('import a\n')
            self.assertEqual(reachable_modules(p, 'main'), ['a', 'b'])

    def test_onefile_portable_build(self):
        spec = (ROOT/'StorageScope.spec').read_text()
        build = (ROOT/'build-engine-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('a.binaries, a.datas', spec)
        self.assertIn("name='StorageScope'", spec)
        self.assertIn('StorageScope-Portable-v', build)
        self.assertIn('verify-portable-release.py',build)
        self.assertIn('Portable binary hash mismatch', build)

    def test_upgrade_e2e_workflow(self):
        workflow = (ROOT/'.github/workflows/windows-upgrade-e2e.yml').read_text()
        self.assertIn('previous_ref:', workflow)
        self.assertIn('Construire-StorageScope.cmd', workflow)
        self.assertIn('qualifier-mise-a-jour-windows.ps1', workflow)
        self.assertIn('if: always()', workflow)

    def test_version(self):
        from storagescope_windows import VERSION
        release=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(VERSION,release)
        self.assertGreaterEqual(tuple(map(int,release.split('.'))),(6,17))
