"""V6.256 regressions for strict, unambiguous capacity-history JSON input.
Synthetic offline data only. Author: Abdelhalim Talbi.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "03-Sources"
SOURCE = SOURCE_ROOT / "storage_capacity_forecast_v6254.py"
sys.path.insert(0, str(SOURCE_ROOT))
SPEC = importlib.util.spec_from_file_location("storage_capacity_forecast_v6256", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StrictCapacityJsonV6256Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.input_path = Path(self.temp.name) / "history.json"

    def write_raw(self, text):
        self.input_path.write_text(text, encoding="utf-8")

    def test_standard_json_and_unicode_extension_are_supported(self):
        raw = (
            '{"schema":"storagescope.capacity-history.v1","assets":[],"samples":[],'
            '"extension":{"label":"baie française","flags":[true,false,null]}}'
        )
        self.write_raw(raw)
        document = MODULE.load_capacity_history(self.input_path)
        self.assertEqual(document["extension"]["label"], "baie française")
        self.assertEqual(document["extension"]["flags"], [True, False, None])

    def test_duplicate_keys_are_rejected_at_root_and_nested_depth(self):
        cases = (
            '{"schema":"wrong","schema":"storagescope.capacity-history.v1","assets":[],"samples":[]}',
            '{"schema":"storagescope.capacity-history.v1","assets":[],"samples":[],'
            '"extension":{"limit":1,"limit":2}}',
            '{"schema":"storagescope.capacity-history.v1","assets":[],"samples":[],'
            '"extension":[{"used_gib":50,"used_gib":99}]}',
        )
        for raw in cases:
            with self.subTest(raw=raw):
                self.write_raw(raw)
                with self.assertRaisesRegex(ValueError, "Duplicate JSON object key"):
                    MODULE.load_capacity_history(self.input_path)

    def test_nonstandard_numeric_constants_are_rejected_even_in_extensions(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token):
                self.write_raw(
                    '{"schema":"storagescope.capacity-history.v1","assets":[],"samples":[],'
                    '"extension":{"ignored_numeric_hint":' + token + '}}'
                )
                with self.assertRaisesRegex(ValueError, "Non-standard JSON numeric constant"):
                    MODULE.load_capacity_history(self.input_path)

    def test_invalid_utf8_is_rejected_without_replacement_decoding(self):
        self.input_path.write_bytes(
            b'{"schema":"storagescope.capacity-history.v1","assets":[],"samples":[]}\xff'
        )
        with self.assertRaises(UnicodeDecodeError):
            MODULE.load_capacity_history(self.input_path)

    def test_cli_rejects_ambiguous_input_and_does_not_emit_a_report(self):
        output_path = Path(self.temp.name) / "report.json"
        self.write_raw(
            '{"schema":"wrong","schema":"storagescope.capacity-history.v1","assets":[],"samples":[]}'
        )
        completed = subprocess.run(
            [sys.executable, str(SOURCE), str(self.input_path), "--output", str(output_path)],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Duplicate JSON object key", completed.stderr)
        self.assertFalse(output_path.exists(), "Invalid input must not produce an assessment report.")

    def test_governance_and_native_windows_workflows_execute_this_regression(self):
        for relative in (
            ".github/workflows/governance-review-qualification.yml",
            ".github/workflows/windows-build.yml",
        ):
            workflow = ROOT / relative
            with self.subTest(workflow=relative):
                self.assertIn("test_storage_capacity_json_strict_v6256.py",
                              workflow.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
