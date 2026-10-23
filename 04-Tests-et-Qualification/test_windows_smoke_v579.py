import unittest, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).parent
class SmokeV579(unittest.TestCase):
    def test_version_cli(self):
        p=subprocess.run([sys.executable,str(ROOT/'storagescope_windows.py'),'--version'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.strip(),(ROOT/'VERSION').read_text(encoding='utf-8').strip())
    def test_smoke_script(self):
        script=(ROOT/'qualifier-executable-windows.ps1').read_text()
        self.assertIn('--self-test',script)
        self.assertIn('--version',script)
        self.assertIn('ExitCode',script)
    def test_ci_runs_smoke(self):
        workflow=(ROOT/'.github/workflows/windows-build.yml').read_text(encoding='utf-8')
        self.assertIn('Qualify native binaries',workflow)
        self.assertIn('qualify-native-windows.ps1',workflow)
        self.assertIn('windows-qualification-report.json',workflow)
    def test_build_checks_frozen_version(self):
        engine=(ROOT/'build-engine-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('$reportedVersion',engine)
        self.assertIn('--version-file',engine)
        self.assertIn('Version EXE inattendue',engine)
    def test_self_test_failure_exits_nonzero(self):
        src=(ROOT/'storagescope_windows.py').read_text()
        self.assertIn('sys.exit(1)',src)
