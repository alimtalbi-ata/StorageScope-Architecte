import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/"02-Compilation-Windows"
class BuildGuardTests(unittest.TestCase):
 def test_unresolved_journal_blocks_build(self):
  s=(ROOT/"build-all-windows.ps1").read_text()
  self.assertIn("$unfinishedJournal",s)
  self.assertIn("Test-Path -LiteralPath $unfinishedJournal",s)
  self.assertLess(s.index("$unfinishedJournal ="),s.index("$stage ="))
 def test_unresolved_backup_blocks_build(self):
  s=(ROOT/"build-all-windows.ps1").read_text()
  self.assertLess(s.index("$unfinishedBackup ="),s.index("$stage ="))
 def test_build_exit_is_checked(self):
  s=(ROOT/"build-all-windows.ps1").read_text()
  self.assertIn('Transactional publication failed',s)
 def test_portable_status_is_visible(self):
  wrapper=(ROOT/"Construire-StorageScope.cmd").read_text(encoding="utf-8")
  outer=(ROOT/"build-all-windows.ps1").read_text(encoding="utf-8")
  engine=(ROOT/"build-engine-windows.ps1").read_text(encoding="utf-8")
  self.assertIn("..\\Construire-StorageScope.cmd", wrapper)
  self.assertIn("exit /b %ERRORLEVEL%", wrapper)
  self.assertIn("build-engine-windows.ps1", outer)
  self.assertIn("verify-portable-release.py", engine)
  self.assertIn("StorageScope-Portable-v", engine)
  self.assertIn("Portable binary hash mismatch", engine)
if __name__=="__main__":unittest.main()
