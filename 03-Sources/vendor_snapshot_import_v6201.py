"""Offline, fail-closed NetApp/PowerScale/FlashBlade inventory adapters.

Only operator-supplied snapshots are accepted; no vendor API or CMDB writes.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

SCHEMA = 'storagescope.vendor-snapshot.v1'
VENDORS = {
    'netapp_ontap': ('serial_number', 'cluster_name', 'capacity_used_bytes', 'capacity_total_bytes', 'volumes', 'uuid'),
    'dell_powerscale': ('serial', 'cluster', 'used_bytes', 'total_bytes', 'exports', 'id'),
    'pure_flashblade': ('array_id', 'name', 'space_used_bytes', 'space_total_bytes', 'shares', 'id'),
}
IDENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
MAX_BYTES = 5_000_000


def _id(value):
    return value if isinstance(value, str) and IDENT.fullmatch(value) else None


def _gib(value):
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError('Capacity must be a nonnegative integer number of bytes')
    return round(value / 1073741824, 6)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON property rejected')
        result[key] = value
    return result


def load_snapshot(path):
    """Bounded, strict JSON reader; rejects duplicate keys and non-finite numbers."""
    source = Path(path)
    if source.stat().st_size > MAX_BYTES:
        raise ValueError('Snapshot exceeds 5 MB')
    with source.open('r', encoding='utf-8-sig') as stream:
        return json.load(stream, object_pairs_hook=_unique_pairs,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))


def normalize(snapshot):
    """Return topology + provenance + quarantine; never silently certify missing data."""
    if not isinstance(snapshot, dict) or snapshot.get('schema') != SCHEMA:
        raise ValueError('Unsupported vendor snapshot schema')
    vendor = snapshot.get('vendor')
    if not isinstance(vendor, str) or vendor not in VENDORS:
        raise ValueError('Unsupported vendor; no generic fallback')
    source_ref = _id(snapshot.get('source_ref'))
    timestamp = snapshot.get('collected_at')
    if not source_ref or not isinstance(timestamp, str) or not timestamp.endswith('Z'):
        raise ValueError('Trusted source_ref and UTC collection time required')
    try:
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid collection timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('UTC timestamp required')
    systems = snapshot.get('systems')
    if not isinstance(systems, list) or len(systems) > 1000:
        raise ValueError('systems must be an array of at most 1000 entries')
    serial_key, name_key, used_key, total_key, shares_key, share_id_key = VENDORS[vendor]
    ids = Counter(_id(s.get(serial_key)) for s in systems if isinstance(s, dict) and _id(s.get(serial_key)))
    duplicate_ids = sorted(k for k, count in ids.items() if count > 1)
    assets, shares, rejected = [], [], []
    seen_shares = set()
    share_count = 0
    for index, system in enumerate(systems):
        if not isinstance(system, dict):
            rejected.append(f'systems[{index}]: not an object')
            continue
        serial = _id(system.get(serial_key))
        if not serial or serial in duplicate_ids:
            rejected.append(f'systems[{index}]: missing or duplicate system identity')
            continue
        try:
            used, total = _gib(system.get(used_key)), _gib(system.get(total_key))
        except ValueError:
            rejected.append(f'systems[{index}]: invalid capacity')
            continue
        if used is not None and total is not None and (total == 0 or used > total):
            rejected.append(f'systems[{index}]: inconsistent capacity')
            continue
        entries = system.get(shares_key, [])
        if not isinstance(entries, list):
            rejected.append(f'systems[{index}]: shares not an array')
            continue
        share_count += len(entries)
        if share_count > 10000:
            raise ValueError('Snapshot exceeds 10000 share records')
        asset_id = f'{vendor}:{serial}'
        asset = {'id': asset_id, 'kind': 'nas', 'vendor': vendor, 'source_ref': source_ref,
                 'collected_at': timestamp}
        if isinstance(system.get(name_key), str):
            asset['name'] = system[name_key]
        if used is not None:
            asset['used_gib'] = used
        if total is not None:
            asset['total_gib'] = total
        assets.append(asset)
        for j, entry in enumerate(entries):
            if not isinstance(entry, dict):
                rejected.append(f'systems[{index}].shares[{j}]: not an object')
                continue
            sid = _id(entry.get(share_id_key))
            protocol = entry.get('protocol')
            share_id = f'{asset_id}:{protocol}:{sid}'
            if not sid or protocol not in ('NFS', 'SMB') or share_id in seen_shares:
                rejected.append(f'systems[{index}].shares[{j}]: invalid or duplicate share identity')
                continue
            try:
                share_used = _gib(entry.get('used_bytes'))
                quota = _gib(entry.get('quota_bytes'))
            except ValueError:
                rejected.append(f'systems[{index}].shares[{j}]: invalid quota')
                continue
            if share_used is not None and quota is not None and (quota == 0 or share_used > quota):
                rejected.append(f'systems[{index}].shares[{j}]: inconsistent quota')
                continue
            seen_shares.add(share_id)
            share = {'id': share_id, 'nas_id': asset_id, 'protocol': protocol,
                     'source_ref': source_ref, 'collected_at': timestamp}
            if share_used is not None:
                share['used_gib'] = share_used
            if quota is not None:
                share['quota_gib'] = quota
            shares.append(share)
    # Duplicate share evidence poisons all shares on that source system.
    duplicates = {s.split(': invalid or duplicate share identity')[0] for s in rejected
                  if s.endswith(': invalid or duplicate share identity')}
    if duplicates:
        bad_system_indices = {int(s.split(']')[0].split('[')[1]) for s in duplicates}
        bad_assets = {f'{vendor}:{_id(systems[i].get(serial_key))}' for i in bad_system_indices}
        shares = [s for s in shares if s['nas_id'] not in bad_assets]
    topology = {'schema': 'storagescope.storage-topology.v1', 'assets': assets,
                'paths': [], 'shares': shares}
    return {'schema': 'storagescope.vendor-import-report.v1', 'vendor': vendor,
            'source_ref': source_ref, 'collected_at': timestamp,
            'topology': topology, 'quarantined_system_ids': duplicate_ids,
            'rejected': sorted(rejected), 'assessment': 'INCOMPLETE' if rejected or duplicate_ids or not assets else 'OBSERVED_ONLY',
            'automatic_changes': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only offline vendor snapshot normalization')
    parser.add_argument('input', help='Vendor snapshot JSON (maximum 5 MB)')
    parser.add_argument('output', help='New normalized report JSON (must not exist)')
    args = parser.parse_args(argv)
    report = normalize(load_snapshot(args.input))
    target = Path(args.output)
    with target.open('x', encoding='utf-8') as stream:
        try:
            json.dump(report, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write('\n')
        except BaseException:
            stream.close()
            target.unlink(missing_ok=True)
            raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
