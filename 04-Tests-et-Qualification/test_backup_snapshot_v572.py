import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from storagescope_windows import application_paths, backup_snapshot, verify_backup_snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = application_paths(self.root / 'data')
        with sqlite3.connect(self.paths['decisions']) as con:
            con.execute('create table sample (x text)')
            con.execute('insert into sample values (?)', ('important',))
        self.paths['views'].write_text('{"views": []}', encoding='utf-8')

    def test_snapshot_valid(self):
        folder, files = backup_snapshot(self.paths, self.root / 'backups')
        self.assertTrue(verify_backup_snapshot(folder))
        self.assertEqual(len(files), 2)
        with sqlite3.connect(folder / 'architecture-decisions.sqlite') as con:
            self.assertEqual(con.execute('select x from sample').fetchone()[0], 'important')

    def test_two_snapshots_never_overwrite(self):
        first, _ = backup_snapshot(self.paths, self.root / 'backups')
        second, _ = backup_snapshot(self.paths, self.root / 'backups')
        self.assertNotEqual(first, second)
        self.assertTrue(verify_backup_snapshot(first))

    def test_tamper_detection(self):
        folder, _ = backup_snapshot(self.paths, self.root / 'backups')
        (folder / 'governance-views.json').write_text('modified', encoding='utf-8')
        self.assertFalse(verify_backup_snapshot(folder))

    def test_no_data_fails_cleanly(self):
        empty = application_paths(self.root / 'empty')
        with self.assertRaisesRegex(ValueError, 'Aucune donnée'):
            backup_snapshot(empty, self.root / 'backups')
        self.assertFalse(list((self.root / 'backups').iterdir()))

    def test_active_directory_rejected(self):
        with self.assertRaises(ValueError):
            backup_snapshot(self.paths, self.paths['base'] / 'subdir')

    def test_manifest_inventory_detection(self):
        folder, _ = backup_snapshot(self.paths, self.root / 'backups')
        (folder / 'unexpected.txt').write_text('extra')
        self.assertFalse(verify_backup_snapshot(folder))
