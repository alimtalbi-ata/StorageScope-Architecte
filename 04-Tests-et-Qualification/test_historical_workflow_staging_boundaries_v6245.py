"""Regression tests for V6.245 workflow fixture staging boundaries.

These tests make the copy/staging boundary explicit: source and destination
trees must be disjoint, broken symlink sources are rejected, and a historical
fixture that appears concurrently must never be overwritten.
Author: Abdelhalim Talbi.
"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_historical_windows_suite import (
    stage_historical_upgrade_workflow,
    stage_workflow_fixtures,
)


class HistoricalWorkflowStagingBoundariesV6245(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.source = self.root / "active-workflows"
        self.source.mkdir()
        self.target = self.root / "historical-tests" / ".github"

    def test_same_source_and_target_tree_is_rejected(self):
        (self.source / "check.yml").write_bytes(b"name: fixture\n")
        original = (self.source / "check.yml").read_bytes()

        with self.assertRaisesRegex(RuntimeError, "must be disjoint"):
            stage_workflow_fixtures(self.source, self.source)

        self.assertEqual((self.source / "check.yml").read_bytes(), original)

    def test_target_nested_inside_source_is_rejected_before_creation(self):
        (self.source / "check.yml").write_bytes(b"name: fixture\n")
        target = self.source / "staged-output"

        with self.assertRaisesRegex(RuntimeError, "must be disjoint"):
            stage_workflow_fixtures(self.source, target)

        self.assertFalse(target.exists())
        self.assertEqual((self.source / "check.yml").read_bytes(), b"name: fixture\n")

    def test_source_nested_inside_target_is_rejected_before_staging(self):
        target = self.root / "fixture-tree"
        source = target / "active"
        source.mkdir(parents=True)
        source_file = source / "check.yml"
        source_file.write_bytes(b"name: fixture\n")

        with self.assertRaisesRegex(RuntimeError, "must be disjoint"):
            stage_workflow_fixtures(source, target)

        self.assertEqual(source_file.read_bytes(), b"name: fixture\n")
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["active"])

    def test_broken_symlink_source_is_not_mistaken_for_missing_tree(self):
        missing = self.root / "broken-source-link"
        # Mock the platform predicate so this contract is deterministic on
        # Windows runners that do not grant developers symlink-creation rights.
        with patch.object(Path, "is_symlink", autospec=True,
                          side_effect=lambda candidate: candidate == missing):
            with self.assertRaisesRegex(RuntimeError, "source is a symbolic link"):
                stage_workflow_fixtures(missing, self.target)

        self.assertFalse(self.target.exists())

    def _create_archived_upgrade_workflow(self):
        sources = self.root / "checkout"
        archived = sources / "Ressources" / ".github" / "workflows" / "windows-upgrade-e2e.yml"
        archived.parent.mkdir(parents=True)
        archived.write_bytes(b"name: v5.89 historical fixture\n")
        tests = self.root / "tests"
        tests.mkdir()
        return sources, tests, archived, tests / ".github" / "workflows" / archived.name

    def test_historical_fixture_existing_conflict_is_preserved(self):
        sources, tests, archived, target = self._create_archived_upgrade_workflow()
        target.parent.mkdir(parents=True)
        original = b"name: separately maintained v5.89 fixture\n"
        target.write_bytes(original)

        with self.assertRaisesRegex(RuntimeError, "existing test asset preserved"):
            stage_historical_upgrade_workflow(sources, tests)

        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(archived.read_bytes(), b"name: v5.89 historical fixture\n")

    def test_historical_fixture_is_idempotent_when_identical(self):
        sources, tests, archived, target = self._create_archived_upgrade_workflow()
        target.parent.mkdir(parents=True)
        target.write_bytes(archived.read_bytes())

        stage_historical_upgrade_workflow(sources, tests)

        self.assertEqual(target.read_bytes(), archived.read_bytes())
        self.assertEqual(list(target.parent.glob("*.staging-*")), [])

    def test_historical_fixture_created_during_promotion_is_not_overwritten(self):
        sources, tests, archived, target = self._create_archived_upgrade_workflow()
        concurrent_bytes = b"name: concurrent preserved fixture\n"
        real_link = os.link

        def create_target_before_link(src, dst):
            Path(dst).write_bytes(concurrent_bytes)
            return real_link(src, dst)

        with patch("scripts.run_historical_windows_suite.os.link",
                   side_effect=create_target_before_link):
            with self.assertRaisesRegex(RuntimeError, "no-overwrite promotion"):
                stage_historical_upgrade_workflow(sources, tests)

        self.assertEqual(target.read_bytes(), concurrent_bytes)
        self.assertEqual(list(target.parent.glob("*.staging-*")), [])
        self.assertEqual(archived.read_bytes(), b"name: v5.89 historical fixture\n")

    def test_historical_symlink_destination_is_rejected(self):
        sources, tests, archived, target = self._create_archived_upgrade_workflow()
        with patch.object(Path, "is_symlink", autospec=True,
                          side_effect=lambda candidate: candidate == target):
            with self.assertRaisesRegex(RuntimeError, "symlink collision"):
                stage_historical_upgrade_workflow(sources, tests)

        self.assertFalse(target.exists())
        self.assertEqual(archived.read_bytes(), b"name: v5.89 historical fixture\n")


if __name__ == "__main__":
    unittest.main()
