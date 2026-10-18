import pathlib, unittest
SCRIPT = pathlib.Path(__file__).resolve().parents[1] / '02-Compilation-Windows/build-all-windows.ps1'
class PublicationRollbackContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.code=SCRIPT.read_text(encoding='utf-8')
    def test_backup_before_promote(self):
        self.assertLess(self.code.index('Move-Item -LiteralPath $to -Destination (Join-Path $backupRoot $dir)'),self.code.index('Move-Item -LiteralPath $from -Destination $to -ErrorAction Stop'))
    def test_reverse_order_rollback(self): self.assertIn('for ($i = $promoted.Count - 1; $i -ge 0; $i--)',self.code)
    def test_backup_recovery(self): self.assertIn('ROLLBACK INCOMPLETE',self.code)
    def test_no_overwrite_existing_backup(self): self.assertIn('Unresolved publication backup: manual recovery required',self.code)
    def test_sha_before_promotion(self): self.assertLess(self.code.index('Get-FileHash'),self.code.index('# Transactional publication'))
if __name__ == '__main__': unittest.main()
