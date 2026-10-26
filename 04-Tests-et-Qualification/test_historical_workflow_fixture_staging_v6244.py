"""Regression tests for safe historical workflow-fixture staging.

An active workflow may be copied into the historical test tree only when it
does not overwrite an existing fixture with different bytes. Author:
Abdelhalim Talbi.
"""
from pathlib import Path
import tempfile
import unittest

from scripts.run_historical_windows_suite import stage_workflow_fixtures


class WorkflowFixtureStagingV6244(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.source = self.root / "active-workflows"
        self.target = self.root / "historical-tests" / ".github"
        self.source.mkdir()

    def test_missing_fixture_is_copied_byte_for_byte(self):
        raw = b"name: workflow\nrun: echo UTF-8 \xc3\xa9\n"
        source = self.source / "workflows" / "check.yml"
        source.parent.mkdir()
        source.write_bytes(raw)

        stage_workflow_fixtures(self.source, self.target)

        self.assertEqual((self.target / "workflows" / "check.yml").read_bytes(), raw)

    def test_identical_existing_fixture_is_idempotent(self):
        relative = Path("workflows") / "known.yml"
        source = self.source / relative
        target = self.target / relative
        source.parent.mkdir(parents=True)
        target.parent.mkdir(parents=True)
        source.write_bytes(b"name: same\n")
        target.write_bytes(b"name: same\n")

        stage_workflow_fixtures(self.source, self.target)
        self.assertEqual(target.read_bytes(), b"name: same\n")
        self.assertEqual(list(self.target.rglob("*.staging-*")), [])

    def test_different_existing_fixture_is_rejected_and_preserved(self):
        relative = Path("workflows") / "historical.yml"
        source = self.source / relative
        target = self.target / relative
        source.parent.mkdir(parents=True)
        target.parent.mkdir(parents=True)
        source.write_bytes(b"name: active-current\n")
        original_fixture = b"name: historical-v589\n"
        target.write_bytes(original_fixture)

        with self.assertRaisesRegex(RuntimeError, "existing test asset preserved"):
            stage_workflow_fixtures(self.source, self.target)

        self.assertEqual(target.read_bytes(), original_fixture)
        self.assertEqual(source.read_bytes(), b"name: active-current\n")
        self.assertEqual(list(self.target.rglob("*.staging-*")), [])

    def test_file_directory_collision_is_rejected(self):
        source = self.source / "windows-upgrade.yml"
        source.write_bytes(b"name: source\n")
        target = self.target / "windows-upgrade.yml"
        target.mkdir(parents=True)
        marker = target / "do-not-delete.txt"
        marker.write_text("fixture stays", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "file/directory collision"):
            stage_workflow_fixtures(self.source, self.target)

        self.assertEqual(marker.read_text(encoding="utf-8"), "fixture stays")

    def test_missing_source_root_is_a_noop(self):
        missing = self.root / "not-present"
        stage_workflow_fixtures(missing, self.target)
        self.assertFalse(self.target.exists())

    def test_concurrent_destination_creation_is_never_overwritten(self):
        source = self.source / "workflows" / "raced.yml"
        source.parent.mkdir()
        source.write_bytes(b"name: source\\n")
        target = self.target / "workflows" / "raced.yml"
        raced_bytes = b"name: concurrent-historical-fixture\\n"

        import os
        real_link = os.link

        def create_target_then_link(src, dst):
            Path(dst).write_bytes(raced_bytes)
            # The no-overwrite primitive must fail because the target now exists.
            return real_link(src, dst)

        from unittest.mock import patch
        with patch("scripts.run_historical_windows_suite.os.link", side_effect=create_target_then_link):
            with self.assertRaisesRegex(RuntimeError, "no-overwrite promotion"):
                stage_workflow_fixtures(self.source, self.target)

        self.assertEqual(target.read_bytes(), raced_bytes)
        self.assertEqual(list(self.target.rglob("*.staging-*")), [])


if __name__ == "__main__":
    unittest.main()
