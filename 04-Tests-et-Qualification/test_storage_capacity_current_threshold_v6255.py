"""V6.255 regression tests for already-reached capacity thresholds.
Synthetic offline observations only. Author: Abdelhalim Talbi.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "03-Sources"))
from storage_capacity_forecast_v6254 import forecast  # noqa: E402


def history(values):
    rows = []
    for day, used in zip((0, 2, 4), values):
        rows.append({
            "asset_id": "array-a",
            "observation_id": f"obs-{day}-{used}",
            "source_ref": "synthetic-fixture",
            "observed_at": f"2026-10-{20 + day:02d}T00:00:00Z",
            "used_gib": used,
            "total_gib": 100,
        })
    return {
        "schema": "storagescope.capacity-history.v1",
        "assets": [{"id": "array-a", "kind": "storage_array", "total_gib": 100}],
        "samples": rows,
    }


class CurrentCapacityThresholdV6255Tests(unittest.TestCase):
    def test_warning_already_reached_still_emits_risk_and_critical_forecast(self):
        report = forecast(history((80, 86, 88)), warning_percent=85, critical_percent=95, horizon_days=10)
        item = report["forecasts"][0]
        codes = {finding["code"] for finding in report["findings"]}
        self.assertEqual(item["status"], "CURRENT_WARNING_THRESHOLD_REACHED")
        self.assertIn("CAPACITY_WARNING_THRESHOLD_CURRENT", codes)
        self.assertIn("CAPACITY_CRITICAL_FORECAST", codes)
        self.assertAlmostEqual(item["days_to_critical"], 3.5)
        self.assertEqual(report["assessment"], "RISKS_FOUND")
        self.assertEqual(report["automatic_changes"], 0)

    def test_critical_already_reached_is_reported_even_when_trend_is_falling(self):
        report = forecast(history((99, 97, 95)), warning_percent=85, critical_percent=95)
        item = report["forecasts"][0]
        codes = {finding["code"] for finding in report["findings"]}
        critical = next(f for f in report["findings"] if f["code"] == "CAPACITY_CRITICAL_THRESHOLD_CURRENT")
        self.assertEqual(item["status"], "CURRENT_CRITICAL_THRESHOLD_REACHED")
        self.assertEqual(critical["level"], "HIGH")
        self.assertIn("CAPACITY_CRITICAL_THRESHOLD_CURRENT", codes)
        self.assertNotIn("CAPACITY_CRITICAL_FORECAST", codes)
        self.assertEqual(report["assessment"], "RISKS_FOUND")

    def test_warning_at_exact_boundary_is_reported_even_when_trend_is_falling(self):
        report = forecast(history((89, 87, 85)), warning_percent=85, critical_percent=95)
        item = report["forecasts"][0]
        self.assertEqual(item["status"], "CURRENT_WARNING_THRESHOLD_REACHED")
        self.assertIn("CAPACITY_WARNING_THRESHOLD_CURRENT", {f["code"] for f in report["findings"]})
        self.assertNotIn("CAPACITY_CRITICAL_FORECAST", {f["code"] for f in report["findings"]})
        self.assertEqual(report["assessment"], "RISKS_FOUND")

    def test_current_critical_threshold_is_reported_at_full_utilization(self):
        report = forecast(history((100, 100, 100)), warning_percent=85, critical_percent=95)
        self.assertEqual(report["forecasts"][0]["status"], "CURRENT_CRITICAL_THRESHOLD_REACHED")
        self.assertTrue(any(f["code"] == "CAPACITY_CRITICAL_THRESHOLD_CURRENT"
                            and f["level"] == "HIGH" for f in report["findings"]))


if __name__ == "__main__":
    unittest.main()
