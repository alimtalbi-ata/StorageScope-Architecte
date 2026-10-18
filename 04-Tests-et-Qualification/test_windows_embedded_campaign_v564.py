"""Embedded campaign integration contract tests. Author: Abdelhalim Talbi."""
import inspect
import unittest
from pathlib import Path
import storagescope_windows as app
from campaign_dashboard_v527 import launch_dashboard
ROOT=Path(__file__).resolve().parent

class EmbeddedCampaignTests(unittest.TestCase):
    def test_version(self): self.assertGreaterEqual(tuple(map(int, app.VERSION.split('.'))), (5, 64))
    def test_embedded_argument(self): self.assertIn('parent',inspect.signature(launch_dashboard).parameters)
    def test_embedded_root(self):
        src=inspect.getsource(launch_dashboard)
        self.assertIn('root = parent if embedded else tk.Tk()',src)
    def test_embedded_does_not_start_event_loop(self):
        src=inspect.getsource(launch_dashboard)
        self.assertIn('if not embedded:\n        root.mainloop()',src)
    def test_shell_uses_embedded(self):
        src=inspect.getsource(app.launch)
        self.assertIn("launch_dashboard(paths['campaigns'], parent=campaigns_page)",src)
    def test_no_subprocess_for_campaigns(self):
        src=inspect.getsource(app.launch)
        self.assertNotIn('subprocess.Popen',src)
    def test_cumulative_packaging(self):
        for name in ('StorageScope.spec','StorageScope.iss','build-windows.ps1','build-installer-windows.ps1'):
            self.assertTrue((ROOT/name).exists())
