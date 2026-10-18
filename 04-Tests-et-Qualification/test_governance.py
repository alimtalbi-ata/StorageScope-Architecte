import tempfile
import unittest
from pathlib import Path
from governance import Governance

class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.g = Governance(Path(self.temp.name)/'test.db')
        self.g.propose('ADR-001','Redondance SAN','Eviter SPOF','architecte')

    def tearDown(self):
        self.g.close()
        self.temp.cleanup()

    def test_self_approval_forbidden(self):
        with self.assertRaises(ValueError): self.g.decide('ADR-001','architecte','APPROVED')

    def test_blocking_reservation(self):
        self.g.add_reservation('RES-001','ADR-001','Preuve PRA','ops')
        with self.assertRaises(ValueError): self.g.decide('ADR-001','comite','APPROVED')
        self.g.resolve_reservation('RES-001','ops','PV recette PRA')
        self.g.decide('ADR-001','comite','APPROVED')
        self.assertTrue(self.g.verify_audit())

    def test_export_hash(self):
        content,digest=self.g.export_markdown()
        self.assertIn('ADR-001',content)
        self.assertEqual(len(digest),64)

    def test_audit_tampering(self):
        self.g.db.execute("UPDATE audit SET actor='intrus' WHERE seq=1")
        self.g.db.commit()
        self.assertFalse(self.g.verify_audit())

if __name__ == '__main__': unittest.main()
