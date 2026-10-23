"""Regression of archived workflow fixture staging (not a native Windows test)."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import unittest

RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "run_historical_windows_suite.py"
spec = importlib.util.spec_from_file_location("historical_runner_v6189", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ArchivedWorkflowFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.sources = root / "03-Sources"
        self.tests = root / "04-Tests-et-Qualification"
        self.archived = self.sources / "Ressources" / ".github" / "workflows" / "windows-upgrade-e2e.yml"
        self.archived.parent.mkdir(parents=True)
        self.archived.write_text("name: archived\n", encoding="utf-8")
        self.target = self.tests / ".github" / "workflows" / self.archived.name

    def test_copy_preserves_archived_bytes(self):
        runner.stage_historical_upgrade_workflow(self.sources, self.tests)
        self.assertEqual(self.target.read_bytes(), self.archived.read_bytes())

    def test_identical_existing_fixture_is_idempotent(self):
        runner.stage_historical_upgrade_workflow(self.sources, self.tests)
        runner.stage_historical_upgrade_workflow(self.sources, self.tests)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "name: archived\n")

    def test_conflicting_fixture_fails_closed(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text("name: different\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "collision"):
            runner.stage_historical_upgrade_workflow(self.sources, self.tests)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "name: different\n")

    def test_missing_archive_without_legacy_test_is_allowed(self):
        self.archived.unlink()
        runner.stage_historical_upgrade_workflow(self.sources, self.tests)
        self.assertFalse(self.target.exists())

    def test_missing_archive_fails_closed(self):
        self.archived.unlink()
        self.tests.mkdir(parents=True)
        (self.tests / "test_windows_portable_v589.py").write_text("# requires workflow\\n", encoding="utf-8")
        with self.assertRaisesRegex(FileNotFoundError, "archived"):
            runner.stage_historical_upgrade_workflow(self.sources, self.tests)
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
