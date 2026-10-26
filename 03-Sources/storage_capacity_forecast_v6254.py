"""Read-only capacity trend forecast from a reconciled SAN/NAS export.

This deterministic tool does not contact devices or write to a CMDB. It requires
explicit source labels and observation IDs, but does not claim those labels are
cryptographically authenticated. Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
import math
import unicodedata
from pathlib import Path

from storage_observation_time_v6215 import parse_observed_at

INPUT_SCHEMA = "storagescope.capacity-history.v1"
OUTPUT_SCHEMA = "storagescope.capacity-forecast.v1"
MAX_SAMPLES = 50_000
MAX_ASSETS = 10_000
MAX_LABEL_LENGTH = 256
MAX_HORIZON_DAYS = 3_650
MINIMUM_POINTS = 3
MINIMUM_SPAN_DAYS = 2.0
LEVEL_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}


def _label(value):
    """Validate an opaque ID/source label without accepting control characters."""
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value)
    if not normalized.strip() or len(normalized) > MAX_LABEL_LENGTH:
        return None
    if any(unicodedata.category(char).startswith("C") or
           unicodedata.category(char) in {"Zl", "Zp"} for char in normalized):
        return None
    return " ".join(normalized.split())


def _finite_number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        if not math.isfinite(value):
            return False
    except (OverflowError, TypeError):
        return False
    return value > 0 if positive else value >= 0


def _threshold(value):
    return _finite_number(value) and value <= 100


def _invalid(index, reason, asset_id=None):
    item = {"sample_index": index, "reason": reason}
    if asset_id is not None:
        item["asset_id"] = asset_id
    return item


def forecast(document, warning_percent=85, critical_percent=95, horizon_days=90):
    """Estimate time to utilization thresholds; invalid or mixed series fail closed."""
    if not isinstance(document, dict) or document.get("schema") != INPUT_SCHEMA:
        raise ValueError(f"Input schema must be {INPUT_SCHEMA}")
    if not _threshold(warning_percent) or not _threshold(critical_percent) or not (
            0 < warning_percent < critical_percent <= 100):
        raise ValueError("Thresholds must be finite numeric percentages satisfying 0 < warning < critical <= 100")
    if not _finite_number(horizon_days, positive=True) or horizon_days > MAX_HORIZON_DAYS:
        raise ValueError(f"horizon_days must be finite and in (0, {MAX_HORIZON_DAYS}]")

    assets, samples = document.get("assets"), document.get("samples")
    if not isinstance(assets, list) or not isinstance(samples, list):
        raise ValueError("assets and samples must be arrays")
    if len(assets) > MAX_ASSETS:
        raise ValueError(f"Inventory exceeds {MAX_ASSETS} assets")
    if len(samples) > MAX_SAMPLES:
        raise ValueError(f"History exceeds {MAX_SAMPLES} samples")

    findings, invalid_records = [], []
    invalid_indices = set()
    invalid_by_asset = defaultdict(set)
    observation_ids = defaultdict(list)
    current_assets = {}
    asset_id_counts = Counter()

    for asset in assets:
        if isinstance(asset, dict):
            ident = _label(asset.get("id"))
            if ident is not None:
                asset_id_counts[ident] += 1
    duplicate_asset_ids = {ident for ident, count in asset_id_counts.items() if count > 1}
    for ident in sorted(duplicate_asset_ids):
        findings.append({"level": "HIGH", "code": "DUPLICATE_ASSET_ID", "object_id": ident,
                         "evidence": f"{asset_id_counts[ident]} current inventory records share this ID",
                         "recommended_action": "Reconcile the current inventory before forecasting"})

    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            findings.append({"level": "HIGH", "code": "INVALID_ASSET", "object_id": f"assets[{index}]",
                             "evidence": "Expected an asset object",
                             "recommended_action": "Correct the inventory export"})
            continue
        ident = _label(asset.get("id"))
        if ident is None:
            findings.append({"level": "HIGH", "code": "INVALID_ASSET_ID", "object_id": f"assets[{index}]",
                             "evidence": "Asset ID is missing, unsafe or too long",
                             "recommended_action": "Correct the inventory identity"})
            continue
        if ident in duplicate_asset_ids or asset.get("kind") not in {"storage_array", "nas"}:
            continue
        total = asset.get("total_gib")
        if not _finite_number(total, positive=True):
            findings.append({"level": "HIGH", "code": "INVALID_CURRENT_CAPACITY", "object_id": ident,
                             "evidence": "Current total_gib must be finite and greater than zero",
                             "recommended_action": "Correct current inventory capacity before forecasting"})
            continue
        current_assets[ident] = {"kind": asset["kind"], "total_gib": total}

    grouped = defaultdict(list)
    sample_counts_by_asset = Counter()
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            invalid_records.append(_invalid(index, "not_object"))
            invalid_indices.add(index)
            continue
        ident = _label(sample.get("asset_id"))
        if ident is not None:
            sample_counts_by_asset[ident] += 1
        reason = None
        if ident is None:
            reason = "invalid_asset_id"
        elif ident not in current_assets:
            reason = "unknown_ambiguous_or_non_storage_asset"
        observation_id = _label(sample.get("observation_id"))
        source_ref = _label(sample.get("source_ref"))
        if reason is None and observation_id is None:
            reason = "invalid_observation_id"
        if reason is None and source_ref is None:
            reason = "invalid_source_ref"
        timestamp_state, timestamp_utc = parse_observed_at(sample)
        instant = None
        if reason is None and timestamp_state != "VALID":
            reason = "invalid_or_timezone_naive_timestamp"
        elif reason is None:
            try:
                instant = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
            except (ValueError, OverflowError):
                reason = "invalid_timestamp"
        used, total = sample.get("used_gib"), sample.get("total_gib")
        if reason is None and (not _finite_number(used) or not _finite_number(total, positive=True) or used > total):
            reason = "invalid_capacity_values"
        if observation_id is not None:
            observation_ids[observation_id].append((index, ident))
        if reason is not None:
            invalid_records.append(_invalid(index, reason, ident))
            invalid_indices.add(index)
            if ident is not None:
                invalid_by_asset[ident].add(reason)
            findings.append({"level": "HIGH", "code": "INVALID_CAPACITY_HISTORY_SAMPLE",
                             "object_id": ident or f"samples[{index}]", "evidence": reason,
                             "recommended_action": "Re-export the affected history row; no forecast uses it"})
            continue
        grouped[ident].append({"index": index, "observation_id": observation_id,
                               "source_ref": source_ref, "instant": instant,
                               "used_gib": used, "total_gib": total})

    # Duplicate observation IDs invalidate every associated series, independent of row order.
    for observation_id, refs in sorted(observation_ids.items()):
        if len(refs) < 2:
            continue
        for index, ident in refs:
            if index not in invalid_indices:
                invalid_records.append(_invalid(index, "duplicate_observation_id", ident))
                invalid_indices.add(index)
                findings.append({"level": "HIGH", "code": "DUPLICATE_OBSERVATION_ID",
                                 "object_id": ident or f"samples[{index}]",
                                 "evidence": "Observation ID is repeated in the supplied history",
                                 "recommended_action": "Re-export unique observations; never choose a winner automatically"})
            if ident is not None:
                invalid_by_asset[ident].add("duplicate_observation_id")

    # A single bad row invalidates the complete series; don't cherry-pick good-looking samples.
    for ident in invalid_by_asset:
        grouped.pop(ident, None)

    forecasts = []
    for ident in sorted(set(grouped) | set(invalid_by_asset)):
        if ident in invalid_by_asset:
            forecasts.append({"asset_id": ident, "status": "INVALID_HISTORY",
                              "sample_count": sample_counts_by_asset[ident],
                              "reasons": sorted(invalid_by_asset[ident])})
            continue
        records = sorted(grouped[ident], key=lambda row: (row["instant"], row["index"]))
        by_time = defaultdict(list)
        for row in records:
            by_time[row["instant"]].append(row)
        duplicate_rows = [row for rows in by_time.values() if len(rows) > 1 for row in rows]
        if duplicate_rows:
            for row in duplicate_rows:
                entry = _invalid(row["index"], "duplicate_timestamp_for_asset", ident)
                if entry not in invalid_records:
                    invalid_records.append(entry)
                invalid_indices.add(row["index"])
            findings.append({"level": "HIGH", "code": "DUPLICATE_CAPACITY_TIMESTAMP", "object_id": ident,
                             "evidence": f"{len(duplicate_rows)} rows map to repeated UTC timestamps",
                             "recommended_action": "Reconcile duplicate telemetry; no trend is inferred"})
            forecasts.append({"asset_id": ident, "status": "DUPLICATE_TIMESTAMP", "sample_count": len(records)})
            continue

        current_total = current_assets[ident]["total_gib"]
        history_totals = {row["total_gib"] for row in records}
        if len(history_totals) != 1 or next(iter(history_totals)) != current_total:
            findings.append({"level": "MEDIUM", "code": "CAPACITY_BASELINE_CHANGED", "object_id": ident,
                             "evidence": "Historical total_gib is not constant or does not match current inventory",
                             "recommended_action": "Split history at capacity expansion/reduction events"})
            forecasts.append({"asset_id": ident, "status": "CAPACITY_BASELINE_CHANGED",
                              "sample_count": len(records)})
            continue

        span_days = (records[-1]["instant"] - records[0]["instant"]).total_seconds() / 86400.0
        if len(records) < MINIMUM_POINTS:
            findings.append({"level": "MEDIUM", "code": "CAPACITY_TREND_UNASSESSED", "object_id": ident,
                             "evidence": f"Need at least {MINIMUM_POINTS} distinct samples; found {len(records)}",
                             "recommended_action": "Collect more timestamped capacity samples"})
            forecasts.append({"asset_id": ident, "status": "INSUFFICIENT_HISTORY",
                              "sample_count": len(records), "sample_span_days": span_days})
            continue
        if span_days < MINIMUM_SPAN_DAYS:
            findings.append({"level": "MEDIUM", "code": "CAPACITY_TREND_UNASSESSED", "object_id": ident,
                             "evidence": f"History spans {span_days:.3f} days; minimum is {MINIMUM_SPAN_DAYS:.1f}",
                             "recommended_action": "Collect samples over a longer period"})
            forecasts.append({"asset_id": ident, "status": "INSUFFICIENT_SPAN",
                              "sample_count": len(records), "sample_span_days": span_days})
            continue

        origin = records[0]["instant"]
        xs = [(row["instant"] - origin).total_seconds() / 86400.0 for row in records]
        ys = [row["used_gib"] / current_total * 100.0 for row in records]
        mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
        denominator = sum((x - mean_x) ** 2 for x in xs)
        if denominator <= 0 or not math.isfinite(denominator):
            findings.append({"level": "HIGH", "code": "CAPACITY_TREND_NUMERICALLY_UNSTABLE", "object_id": ident,
                             "evidence": "Regression time axis is not numerically usable",
                             "recommended_action": "Review timestamps and history span"})
            forecasts.append({"asset_id": ident, "status": "NUMERICALLY_UNSTABLE",
                              "sample_count": len(records), "sample_span_days": span_days})
            continue
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
        latest_percent = ys[-1]
        result = {"asset_id": ident, "status": "FORECAST_AVAILABLE",
                  "sample_count": len(records), "sample_span_days": span_days,
                  "latest_utilization_percent": latest_percent,
                  "growth_percentage_points_per_day": slope,
                  "forecast_horizon_days": horizon_days,
                  "model": "ordinary_least_squares_linear_utilization"}

        # A current threshold breach is a present risk, even when usage is falling.
        # Report it before the non-growing-series shortcut so it cannot disappear.
        if latest_percent >= critical_percent:
            result["status"] = "CURRENT_CRITICAL_THRESHOLD_REACHED"
            findings.append({
                "level": "HIGH", "code": "CAPACITY_CRITICAL_THRESHOLD_CURRENT",
                "object_id": ident,
                "evidence": (f"Current utilization {latest_percent:.2f}% is at or above "
                             f"the critical threshold {critical_percent:.2f}%"),
                "recommended_action": "Escalate to the storage owner and review capacity immediately"
            })
            forecasts.append(result)
            continue

        if latest_percent >= warning_percent:
            result["status"] = "CURRENT_WARNING_THRESHOLD_REACHED"
            findings.append({
                "level": "MEDIUM", "code": "CAPACITY_WARNING_THRESHOLD_CURRENT",
                "object_id": ident,
                "evidence": (f"Current utilization {latest_percent:.2f}% is at or above "
                             f"the warning threshold {warning_percent:.2f}%"),
                "recommended_action": "Review capacity headroom and the storage growth plan"
            })
            # The warning threshold is already reached, but a rising series can still
            # estimate time to the critical threshold for planning purposes.
            if slope > 0:
                days_critical = (critical_percent - latest_percent) / slope
                result.update({"days_to_critical": days_critical,
                               "critical_within_horizon": days_critical <= horizon_days})
                if days_critical <= horizon_days:
                    findings.append({
                        "level": "HIGH", "code": "CAPACITY_CRITICAL_FORECAST", "object_id": ident,
                        "evidence": (f"Current utilization {latest_percent:.2f}%; trend {slope:.4f} "
                                     f"percentage points/day; critical threshold estimated in "
                                     f"{days_critical:.2f} days (horizon {horizon_days:g} days)"),
                        "recommended_action": "Validate with the storage owner and plan expansion"
                    })
            forecasts.append(result)
            continue

        if slope <= 0:
            result["status"] = "NON_GROWING"
            forecasts.append(result)
            continue

        days_warning = (warning_percent - latest_percent) / slope
        days_critical = (critical_percent - latest_percent) / slope
        result.update({"days_to_warning": days_warning, "days_to_critical": days_critical,
                       "warning_within_horizon": days_warning <= horizon_days,
                       "critical_within_horizon": days_critical <= horizon_days})
        if days_warning <= horizon_days:
            findings.append({"level": "MEDIUM", "code": "CAPACITY_WARNING_FORECAST", "object_id": ident,
                             "evidence": (f"Current utilization {latest_percent:.2f}%; trend {slope:.4f} "
                                          f"percentage points/day; warning estimated in {days_warning:.2f} days "
                                          f"(horizon {horizon_days:g} days)"),
                             "recommended_action": "Review forecast assumptions and plan capacity before warning"})
        if days_critical <= horizon_days:
            findings.append({"level": "HIGH", "code": "CAPACITY_CRITICAL_FORECAST", "object_id": ident,
                             "evidence": (f"Current utilization {latest_percent:.2f}%; trend {slope:.4f} "
                                          f"percentage points/day; critical threshold estimated in "
                                          f"{days_critical:.2f} days (horizon {horizon_days:g} days)"),
                             "recommended_action": "Validate with the storage owner and plan expansion"})
        forecasts.append(result)

    findings.sort(key=lambda item: (LEVEL_ORDER.get(item["level"], 99), item["code"], item["object_id"], item["evidence"]))
    invalid_records.sort(key=lambda item: (item["sample_index"], item["reason"]))
    statuses = {item["status"] for item in forecasts}
    incomplete = {"INVALID_HISTORY", "DUPLICATE_TIMESTAMP", "CAPACITY_BASELINE_CHANGED",
                  "INSUFFICIENT_HISTORY", "INSUFFICIENT_SPAN", "NUMERICALLY_UNSTABLE"}
    if not samples:
        assessment = "NO_DATA"
    elif invalid_records or statuses.intersection(incomplete) or any(
            item["code"] in {"INVALID_ASSET", "INVALID_ASSET_ID", "DUPLICATE_ASSET_ID", "INVALID_CURRENT_CAPACITY"}
            for item in findings):
        assessment = "INCOMPLETE"
    elif findings:
        assessment = "RISKS_FOUND"
    else:
        assessment = "NO_FINDINGS_WITHIN_HORIZON"
    return {
        "schema": OUTPUT_SCHEMA, "assessment": assessment,
        "samples_received": len(samples),
        "valid_samples": len(samples) - len({item["sample_index"] for item in invalid_records}),
        "invalid_sample_count": len({item["sample_index"] for item in invalid_records}),
        "current_storage_assets": len(current_assets), "forecast_assets": len(forecasts),
        "warning_threshold_percent": warning_percent, "critical_threshold_percent": critical_percent,
        "horizon_days": horizon_days, "minimum_points": MINIMUM_POINTS,
        "minimum_span_days": MINIMUM_SPAN_DAYS, "forecasts": forecasts, "findings": findings,
        "invalid_records": invalid_records, "automatic_changes": 0,
        "provenance_note": ("source_ref and observation_id are supplied labels, not independent attestation; "
                            "timestamps are parsed but not proven fresh. Linear extrapolation is a planning signal, "
                            "not a guarantee. No network collection or CMDB writes are performed.")
    }


def _capacity_json_object(pairs):
    """Build a JSON object while rejecting duplicate member names at every depth."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _capacity_json_constant(token):
    """Reject NaN/Infinity extensions that are not part of standard JSON."""
    raise ValueError(f"Non-standard JSON numeric constant: {token}")


def load_capacity_history(path: Path):
    """Read UTF-8 JSON with unambiguous keys and standard finite numeric tokens only."""
    payload = Path(path).read_text(encoding="utf-8")
    return json.loads(
        payload,
        object_pairs_hook=_capacity_json_object,
        parse_constant=_capacity_json_constant,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only SAN/NAS capacity trend forecast")
    parser.add_argument("input", type=Path, help="UTF-8 JSON matching storagescope.capacity-history.v1")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--warning-percent", type=float, default=85)
    parser.add_argument("--critical-percent", type=float, default=95)
    parser.add_argument("--horizon-days", type=float, default=90)
    args = parser.parse_args(argv)
    document = load_capacity_history(args.input)
    report = forecast(document, args.warning_percent, args.critical_percent, args.horizon_days)
    payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 2 if report["assessment"] in {"NO_DATA", "INCOMPLETE"} else (
        1 if report["assessment"] == "RISKS_FOUND" else 0)


if __name__ == "__main__":
    raise SystemExit(main())
