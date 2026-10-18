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
  self.assertIn('portable', (ROOT/"Construire-StorageScope.cmd").read_text().lower())
if __name__=="__main__":unittest.main()
