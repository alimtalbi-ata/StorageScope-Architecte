"""Headless tests of Windows desktop launcher and local paths."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import storagescope_windows as app

class WindowsLauncherTests(unittest.TestCase):
    def test_local_app_data(self):
        self.assertEqual(app.user_data_dir({'LOCALAPPDATA':r'C:\Users\Test\AppData\Local'}).name,'StorageScope')
    def test_app_data_fallback(self):
        self.assertEqual(app.user_data_dir({'APPDATA':r'C:\Users\Test\AppData\Roaming'}).name,'StorageScope')
    def test_paths_created(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=app.application_paths(Path(folder)/'data')
            self.assertTrue(paths['base'].is_dir())
            self.assertEqual(paths['decisions'].name,'architecture-decisions.sqlite')
            self.assertEqual(paths['campaigns'].name,'campaigns.sqlite')
            self.assertEqual(paths['views'].suffix,'.json')
    def test_unknown_argument_rejected(self):
        with self.assertRaises(SystemExit): app.main(['--invalid'])
    def test_benchmark_requires_database(self):
        with self.assertRaises(SystemExit): app.main(['--benchmarks'])
    def test_main_dispatch(self):
        with patch.object(app,'launch') as launcher:
            app.main([])
            launcher.assert_called_once_with()

if __name__ == '__main__': unittest.main()
