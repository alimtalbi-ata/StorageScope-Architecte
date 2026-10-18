import tempfile
import unittest
from pathlib import Path
from graph_freshness import database_fingerprint

class FreshnessTests(unittest.TestCase):
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'missing.sqlite3'
            self.assertEqual(database_fingerprint(f),database_fingerprint(f))
            self.assertIsNone(database_fingerprint(f)[0][1])
    def test_database_write_invalidates(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'db.sqlite3';f.write_bytes(b'a')
            old=database_fingerprint(f);f.write_bytes(b'abcdef')
            self.assertNotEqual(old,database_fingerprint(f))
    def test_wal_create_and_delete_invalidates(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'db.sqlite3';f.write_bytes(b'a')
            old=database_fingerprint(f)
            wal=Path(str(f)+'-wal');wal.write_bytes(b'wal')
            self.assertNotEqual(old,database_fingerprint(f))
            wal.unlink();self.assertEqual(old,database_fingerprint(f))
    def test_shm_write_invalidates(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'db.sqlite3';f.write_bytes(b'a')
            shm=Path(str(f)+'-shm');shm.write_bytes(b'1')
            old=database_fingerprint(f);shm.write_bytes(b'2222')
            self.assertNotEqual(old,database_fingerprint(f))
if __name__=='__main__':unittest.main()
