"""Frozen smoke must not create user data and trigger an upgrade backup gate.

Author: Abdelhalim Talbi.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import storagescope_windows as app


class FrozenSelfTestIsolation(unittest.TestCase):
    def test_smoke_uses_temporary_directory_not_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            user_data = Path(tmp) / "user-data"
            observed = []

            def capture(paths):
                base = Path(paths["base"])
                self.assertTrue(base.is_dir())
                self.assertNotEqual(base, user_data)
                observed.append(base)
                return 0

            with patch.object(app, "user_data_dir", return_value=user_data):
                with patch("windows_release_check_v567.runtime_self_test", side_effect=capture):
                    self.assertEqual(app.main(["--self-test"]), 0)
            self.assertFalse(user_data.exists(), "Self-test must not create persistent user data")
            self.assertEqual(len(observed), 1)
            self.assertFalse(observed[0].exists(), "Temporary self-test data must be removed")

    def test_failure_also_cleans_temporary_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            observed = []

            def fail(paths):
                observed.append(Path(paths["base"]))
                raise RuntimeError("synthetic smoke failure")

            with patch.object(app, "user_data_dir", return_value=Path(tmp) / "user-data"):
                with patch("windows_release_check_v567.runtime_self_test", side_effect=fail):
                    with self.assertRaisesRegex(RuntimeError, "synthetic smoke failure"):
                        app.main(["--self-test"])
            self.assertEqual(len(observed), 1)
            self.assertFalse(observed[0].exists())
            self.assertFalse((Path(tmp) / "user-data").exists())


if __name__ == "__main__":
    unittest.main()
