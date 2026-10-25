"""V6.240 — strict operator auth-enforcement configuration parsing.

Synthetic/offline policy tests only. Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "03-Sources"))
from storage_observation_auth_v6219 import load_auth_policy


def policy(schema: str = "v1") -> dict:
    if schema == "v1":
        source_keys = {"collector:approved": "COLLECTOR_A"}
        schema_name = "storagescope.observation-auth-policy.v1"
    else:
        source_keys = {"collector:approved": ["COLLECTOR_OLD", "COLLECTOR_NEW"]}
        schema_name = "storagescope.observation-auth-policy.v2"
    return {"schema": schema_name, "source_keys": source_keys}


class StrictAuthEnforcementConfigV6240(unittest.TestCase):
    def test_invalid_v2_switch_is_rejected_even_when_policy_exists(self):
        for setting in ("", "true", "2", "disabled", " 0"):
            with self.subTest(setting=setting), patch.dict(
                os.environ,
                {
                    "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH": "0",
                    "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2": setting,
                },
            ):
                with self.assertRaisesRegex(
                    ValueError, "Invalid observation authentication v2 enforcement setting"
                ):
                    load_auth_policy({"observation_auth_policy": policy("v1")})

    def test_invalid_v2_switch_is_rejected_before_missing_policy_branch(self):
        with patch.dict(
            os.environ,
            {
                "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH": "0",
                "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2": "yes",
            },
        ):
            with self.assertRaisesRegex(
                ValueError, "Invalid observation authentication v2 enforcement setting"
            ):
                load_auth_policy({})

    def test_v1_compatibility_and_explicit_v2_requirement_are_preserved(self):
        with patch.dict(
            os.environ,
            {
                "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH": "0",
                "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2": "0",
            },
        ):
            self.assertEqual(
                load_auth_policy({"observation_auth_policy": policy("v1")}),
                {"collector:approved": "COLLECTOR_A"},
            )
        with patch.dict(
            os.environ,
            {
                "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH": "0",
                "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2": "1",
            },
        ):
            with self.assertRaisesRegex(ValueError, "requires observation authentication policy v2"):
                load_auth_policy({"observation_auth_policy": policy("v1")})
            self.assertEqual(
                load_auth_policy({"observation_auth_policy": policy("v2")}),
                {"collector:approved": ("COLLECTOR_OLD", "COLLECTOR_NEW")},
            )

    def test_invalid_primary_switch_still_fails_closed_with_v2_policy(self):
        with patch.dict(
            os.environ,
            {
                "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH": "on",
                "STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2": "1",
            },
        ):
            with self.assertRaisesRegex(ValueError, "Invalid observation authentication enforcement setting"):
                load_auth_policy({"observation_auth_policy": policy("v2")})


if __name__ == "__main__":
    unittest.main()
