"""Tests for privacy-safe diagnostic reporting. Author: Abdelhalim Talbi."""
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "03-Sources" / "windows_support_diagnostic_v619.py"
spec = importlib.util.spec_from_file_location("support_diagnostic", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SupportDiagnosticTests(unittest.TestCase):
    def test_read_only_and_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "secret-decisions.sqlite"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE confidential (value TEXT)")
                conn.execute("INSERT INTO confidential VALUES ('SECRET-PAYLOAD')")
            paths = {"decisions": db, "campaigns": root / "missing.sqlite",
                     "preferences": root / "prefs.json"}
            report = module.collect(paths, "6.108")
            rendered = module.render(report)
            serialized = json.dumps(report)
            self.assertEqual(report["checks"]["decisions"]["status"], "OK")
            self.assertEqual(report["checks"]["campaigns"]["status"], "MISSING")
            self.assertEqual(report["summary"], {"OK": 1, "MISSING": 2, "ERROR": 0})
            for sensitive in ("SECRET-PAYLOAD", str(root), str(db)):
                self.assertNotIn(sensitive, rendered)
                self.assertNotIn(sensitive, serialized)
            self.assertFalse(paths["campaigns"].exists())
            target = root / "support.json"
            module.export_json(report, target)
            self.assertEqual(json.loads(target.read_text())["schema"], report["schema"])
            with self.assertRaises(FileExistsError):
                module.export_json(report, target)

    def test_corrupt_sqlite_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corrupt = root / "bad.sqlite"
            corrupt.write_bytes(b"not a SQLite database")
            link = root / "link.sqlite"
            try:
                link.symlink_to(corrupt)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable on this platform")
            self.assertEqual(module._sqlite_state(corrupt)["status"], "ERROR")
            self.assertEqual(module._sqlite_state(link)["reason"], "symbolic link")

if __name__ == "__main__":
    unittest.main()
