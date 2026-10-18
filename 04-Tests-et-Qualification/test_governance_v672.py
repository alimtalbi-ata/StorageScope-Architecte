"""v6.72: UI and packaging regression contracts. Author: Abdelhalim Talbi."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReleaseContract(unittest.TestCase):
 def test_scrollbars_and_keyboard_search(self):
  code=(ROOT/'03-Sources/governance_desktop.py').read_text(encoding='utf-8')
  for fragment in ('table_scroll=ttk.Scrollbar','details_scroll=ttk.Scrollbar',"root.bind('<Control-f>'",'set_details(content)','selected()  # Re-render details'):
   self.assertIn(fragment,code)
 def test_portable_zip_and_data_separation(self):
  code=(ROOT/'02-Compilation-Windows/build-engine-windows.ps1').read_text(encoding='utf-8')
  for fragment in ('Compress-Archive','StorageScope-Portable-v','portable-zip-sha256','LOCALAPPDATA'):
   self.assertIn(fragment,code)
 def test_staged_native_qualification(self):
  code=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text(encoding='utf-8')
  self.assertIn("'qualify-native-windows.ps1'",code)
  self.assertIn("'qualify-installer-smoke-windows.ps1'",code)
 def test_version_consistency(self):
  version=(ROOT/'07-Manifestes/VERSION').read_text().strip()
  self.assertRegex(version,r'^6\.\d+$')
  self.assertIn("VERSION = '"+version+"'",(ROOT/'03-Sources/storagescope_windows.py').read_text())
if __name__=='__main__':unittest.main()
