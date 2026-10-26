"""V6.254 capacity trend forecast regressions; synthetic offline data only.
Author: Abdelhalim Talbi.
"""
import copy
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "03-Sources"
sys.path.insert(0, str(SOURCE_ROOT))
SOURCE = SOURCE_ROOT / "storage_capacity_forecast_v6254.py"
SPEC = importlib.util.spec_from_file_location("storage_capacity_forecast_v6254", SOURCE)
FORECAST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FORECAST)


def doc(samples, assets=None):
    return {
        "schema": "storagescope.capacity-history.v1",
        "assets": assets if assets is not None else [
            {"id": "array-a", "kind": "storage_array", "total_gib": 100},
        ],
        "samples": samples,
    }


def sample(day, used, *, ident="array-a", observation_id=None, source_ref="collector-a", timestamp=None, total=100):
    return {
        "asset_id": ident,
        "observation_id": observation_id or f"obs-{ident}-{day}-{used}",
        "source_ref": source_ref,
        "observed_at": timestamp or f"2026-10-{20 + day:02d}T00:00:00Z",
        "used_gib": used, "total_gib": total,
    }


class CapacityForecastV6254Tests(unittest.TestCase):
    def codes(self, report):
        return {finding["code"] for finding in report["findings"]}

    def test_growth_forecasts_warning_and_critical_thresholds(self):
        report = FORECAST.forecast(doc([sample(0, 50), sample(2, 60), sample(4, 70)]), horizon_days=10)
        self.assertEqual(report["assessment"], "RISKS_FOUND")
        self.assertIn("CAPACITY_WARNING_FORECAST", self.codes(report))
        self.assertIn("CAPACITY_CRITICAL_FORECAST", self.codes(report))
        row = report["forecasts"][0]
        self.assertAlmostEqual(row["growth_percentage_points_per_day"], 5.0)
        self.assertAlmostEqual(row["days_to_warning"], 3.0)
        self.assertAlmostEqual(row["days_to_critical"], 5.0)
        self.assertEqual(report["automatic_changes"], 0)

    def test_forecast_is_independent_of_input_order(self):
        rows = [sample(0, 50), sample(2, 60), sample(4, 70)]
        self.assertEqual(FORECAST.forecast(doc(rows), horizon_days=10),
                         FORECAST.forecast(doc(list(reversed(rows))), horizon_days=10))

    def test_non_growing_series_does_not_predict_shortage(self):
        report = FORECAST.forecast(doc([sample(0, 70), sample(2, 65), sample(4, 60)]))
        self.assertEqual(report["forecasts"][0]["status"], "NON_GROWING")
        self.assertNotIn("CAPACITY_WARNING_FORECAST", self.codes(report))
        self.assertNotIn("CAPACITY_CRITICAL_FORECAST", self.codes(report))

    def test_insufficient_points_fail_closed(self):
        report = FORECAST.forecast(doc([sample(0, 50), sample(4, 60)]))
        self.assertEqual(report["assessment"], "INCOMPLETE")
        self.assertEqual(report["forecasts"][0]["status"], "INSUFFICIENT_HISTORY")
        self.assertIn("CAPACITY_TREND_UNASSESSED", self.codes(report))

    def test_short_span_fails_closed_even_with_three_samples(self):
        rows = [sample(0, 50, observation_id="o1", timestamp="2026-10-20T00:00:00Z"),
                sample(0, 51, observation_id="o2", timestamp="2026-10-20T12:00:00Z"),
                sample(0, 52, observation_id="o3", timestamp="2026-10-21T00:00:00Z")]
        report = FORECAST.forecast(doc(rows))
        self.assertEqual(report["assessment"], "INCOMPLETE")
        self.assertEqual(report["forecasts"][0]["status"], "INSUFFICIENT_SPAN")

    def test_equivalent_utc_timestamps_are_duplicate_and_quarantined(self):
        rows = [sample(0, 50, observation_id="o1", timestamp="2026-10-20T00:00:00Z"),
                sample(1, 51, observation_id="o2", timestamp="2026-10-20T02:00:00+02:00"),
                sample(2, 52, observation_id="o3", timestamp="2026-10-22T00:00:00Z")]
        report = FORECAST.forecast(doc(rows))
        self.assertEqual(report["assessment"], "INCOMPLETE")
        self.assertEqual(report["forecasts"][0]["status"], "DUPLICATE_TIMESTAMP")
        self.assertIn("DUPLICATE_CAPACITY_TIMESTAMP", self.codes(report))

    def test_capacity_expansion_invalidates_mixed_baseline(self):
        rows = [sample(0, 50, total=100), sample(2, 60, total=100), sample(4, 70, total=200)]
        assets = [{"id": "array-a", "kind": "storage_array", "total_gib": 200}]
        report = FORECAST.forecast(doc(rows, assets))
        self.assertEqual(report["assessment"], "INCOMPLETE")
        self.assertEqual(report["forecasts"][0]["status"], "CAPACITY_BASELINE_CHANGED")
        self.assertIn("CAPACITY_BASELINE_CHANGED", self.codes(report))

    def test_duplicate_observation_id_quarantines_series(self):
        rows = [sample(0, 50, observation_id="duplicate"), sample(2, 60, observation_id="duplicate"),
                sample(4, 70, observation_id="unique")]
        report = FORECAST.forecast(doc(rows))
        self.assertEqual(report["forecasts"][0]["status"], "INVALID_HISTORY")
        self.assertIn("DUPLICATE_OBSERVATION_ID", self.codes(report))
        self.assertEqual(report["automatic_changes"], 0)

    def test_unknown_asset_and_non_storage_kind_are_rejected(self):
        rows = [sample(0, 50, ident="missing"), sample(2, 60, ident="missing"),
                sample(4, 70, ident="missing")]
        report = FORECAST.forecast(doc(rows))
        self.assertEqual(report["assessment"], "INCOMPLETE")
        self.assertIn("INVALID_CAPACITY_HISTORY_SAMPLE", self.codes(report))
        assets = [{"id": "array-a", "kind": "host", "total_gib": 100}]
        report = FORECAST.forecast(doc([sample(0, 50), sample(2, 60), sample(4, 70)], assets))
        self.assertEqual(report["assessment"], "INCOMPLETE")

    def test_malformed_timezone_capacity_and_source_are_quarantined(self):
        rows = [sample(0, 50, timestamp="2026-10-20T00:00:00"),
                sample(2, True), sample(4, 70, source_ref="\ncollector")]
        report = FORECAST.forecast(doc(rows))
        self.assertEqual(report["assessment"], "INCOMPLETE")
        self.assertEqual(report["valid_samples"], 0)
        self.assertTrue(all(item["status"] == "INVALID_HISTORY" for item in report["forecasts"]))

    def test_duplicate_current_asset_id_fails_closed(self):
        assets = [{"id": "array-a", "kind": "storage_array", "total_gib": 100},
                  {"id": "array-a", "kind": "storage_array", "total_gib": 100}]
        report = FORECAST.forecast(doc([sample(0, 50), sample(2, 60), sample(4, 70)], assets))
        self.assertEqual(report["assessment"], "INCOMPLETE")
        self.assertIn("DUPLICATE_ASSET_ID", self.codes(report))
        self.assertIn("INVALID_CAPACITY_HISTORY_SAMPLE", self.codes(report))

    def test_invalid_schema_thresholds_and_horizon_are_rejected(self):
        with self.assertRaises(ValueError):
            FORECAST.forecast({})
        for warning, critical in ((True, 95), (85, False), (math.nan, 95), (85, math.inf), (85, 85)):
            with self.subTest(warning=warning, critical=critical):
                with self.assertRaises(ValueError):
                    FORECAST.forecast(doc([]), warning, critical)
        for horizon in (True, 0, -1, math.nan, math.inf, 3651, 10 ** 400):
            with self.subTest(horizon=horizon):
                with self.assertRaises(ValueError):
                    FORECAST.forecast(doc([]), horizon_days=horizon)

    def test_deterministic_read_only_report_and_cli_json(self):
        document = doc([sample(0, 50), sample(2, 60), sample(4, 70)])
        before = copy.deepcopy(document)
        self.assertEqual(FORECAST.forecast(document, horizon_days=10),
                         FORECAST.forecast(document, horizon_days=10))
        self.assertEqual(document, before)
        with tempfile.TemporaryDirectory() as tmp:
            input_path, output_path = Path(tmp) / "history.json", Path(tmp) / "report.json"
            input_path.write_text(json.dumps(document), encoding="utf-8")
            import subprocess
            completed = subprocess.run([sys.executable, str(SOURCE), str(input_path), "--output",
                                        str(output_path), "--horizon-days", "10"],
                                       text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["automatic_changes"], 0)


if __name__ == "__main__":
    unittest.main()
