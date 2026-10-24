"""Windows release gate tests. Author: Abdelhalim Talbi."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import storagescope_windows as app
from windows_release_check_v567 import runtime_self_test

class WindowsReleaseTests(unittest.TestCase):
    def test_self_test_without_graphical_session(self):
        with tempfile.TemporaryDirectory() as folder:
            with contextlib.redirect_stdout(io.StringIO()) as capture:
                result = runtime_self_test(app.application_paths(folder))
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(capture.getvalue())['status'], 'PASS')
    def test_self_test_cli_dispatch(self):
        with patch('windows_release_check_v567.runtime_self_test', return_value=0) as probe:
            with tempfile.TemporaryDirectory() as folder:
                with patch.object(app,'application_paths',return_value=app.application_paths(folder)):
                    self.assertEqual(app.main(['--self-test']), 0)
            probe.assert_called_once()
    def test_no_gui_started_by_self_test(self):
        with patch.object(app,'launch', side_effect=AssertionError('GUI launched')):
            with tempfile.TemporaryDirectory() as folder:
                with patch.object(app,'application_paths',return_value=app.application_paths(folder)):
                    with contextlib.redirect_stdout(io.StringIO()):
                        app.main(['--self-test'])
    def test_context_menu_contains_standard_actions(self):
        source=(Path(__file__).parent/'windows_context_menu_v567.py').read_text()
        for action in ('Couper','Copier','Coller','Tout sélectionner','Effacer'):
            self.assertIn(action,source)
    def test_installer_version_matches_runtime(self):
        root=Path(__file__).parent
        release=(root/'VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(app.VERSION,release)
        self.assertIn(f'#define AppVersion "{release}"',(root/'StorageScope.iss').read_text(encoding='utf-8'))
    def test_ci_includes_frozen_probe(self):
        root=Path(__file__).parent
        workflow=(root/'.github/workflows/windows-build.yml').read_text(encoding='utf-8')
        engine=(root/'build-engine-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('Qualify native binaries',workflow)
        self.assertIn('windows-qualification-report.json',workflow)
        self.assertIn('--version-file',engine)
        self.assertIn('--self-test',engine)

if __name__=='__main__': unittest.main()
