import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class PublicationRecovery(unittest.TestCase):
 def test_crash_guard_before_build(self):
  s=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text(encoding='utf-8')
  self.assertLess(s.index('$unfinishedBackup ='),s.index("$stage = Join-Path"))
  self.assertIn('Test-Path -LiteralPath $unfinishedBackup',s)
 def test_preserve_pending_when_backup_exists(self):
  s=(ROOT/'02-Compilation-Windows/build-all-windows.ps1').read_text(encoding='utf-8')
  self.assertIn("Test-Path -LiteralPath $unfinishedBackup",s)
  self.assertIn("Restaurer manuellement",s)
 def test_recovery_inspection_read_only(self):
  s=(ROOT/'02-Compilation-Windows/inspect-publication-recovery.ps1').read_text(encoding='utf-8')
  self.assertIn('Test-Path',s)
  self.assertNotIn('Remove-Item',s)
  self.assertNotIn('Move-Item',s)
 def test_recovery_uses_four_components(self):
  s=(ROOT/'02-Compilation-Windows/inspect-publication-recovery.ps1').read_text(encoding='utf-8')
  for d in ('dist','installer','portable','build-logs'): self.assertIn("'"+d+"'",s)
if __name__=='__main__': unittest.main()
