"""V6.253: finite, numeric capacity-threshold contract (synthetic offline tests).
Author: Abdelhalim Talbi.
"""
import importlib.util
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "03-Sources" / "storage_path_risk_v6194.py"
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("storage_path_risk_v6194_v6253", SOURCE)
RISK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RISK)


def empty_topology():
    return {
        "schema": "storagescope.storage-topology.v1",
        "assets": [],
        "paths": [],
        "shares": [],
    }


class CapacityThresholdTypeSafetyV6253(unittest.TestCase):
    def test_boolean_thresholds_are_rejected(self):
        # bool subclasses int, but True/False must never silently become
        # 1%/0% utilization policy.
        for warning, critical in (
            (True, 95),
            (False, 95),
            (85, True),
            (85, False),
        ):
            with self.subTest(warning=warning, critical=critical):
                with self.assertRaises(ValueError):
                    RISK.assess(empty_topology(), warning, critical)

    def test_non_numeric_and_non_finite_thresholds_are_rejected(self):
        invalid_values = (
            None,
            "85",
            complex(85, 0),
            math.nan,
            math.inf,
            -math.inf,
            10 ** 400,
        )
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    RISK.assess(empty_topology(), value, 95)
                with self.assertRaises(ValueError):
                    RISK.assess(empty_topology(), 85, value)

    def test_finite_integer_and_float_thresholds_keep_same_policy(self):
        integer_report = RISK.assess(empty_topology(), 85, 95)
        float_report = RISK.assess(empty_topology(), 85.0, 95.0)
        self.assertEqual(integer_report, float_report)
        self.assertEqual(integer_report["automatic_changes"], 0)

    def test_threshold_validation_does_not_mutate_topology(self):
        topology = empty_topology()
        before = {key: list(value) if isinstance(value, list) else value
                  for key, value in topology.items()}
        RISK.assess(topology, 85, 95)
        self.assertEqual(topology, before)


if __name__ == "__main__":
    unittest.main()
