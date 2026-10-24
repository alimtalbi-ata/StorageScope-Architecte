"""Testable, read-only NAS inventory presentation and CSV export.

Author: Abdelhalim Talbi.
"""
import csv
import shutil
import tempfile
from pathlib import Path

HEADERS = ('Fournisseur', 'Système', 'Identifiant', 'Utilisé GiB', 'Total GiB', 'Partages')


def inventory_rows(report):
    topology = report['topology']
    shares = topology['shares']
    counts = {}
    share_index = {}
    for share in shares:
        system_id = share['nas_id']
        counts[system_id] = counts.get(system_id, 0) + 1
        share_index.setdefault(system_id, []).append(share)
    rows = [
        (asset['vendor'], asset.get('name', '—'), asset['id'],
         asset.get('used_gib', '—'), asset.get('total_gib', '—'),
         counts.get(asset['id'], 0))
        for asset in topology['assets']
    ]
    return rows, share_index


def safe_csv_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text


def export_inventory_csv(rows, destination):
    """Exclusive CSV creation; preserve existing files and clean partial output."""
    target = Path(destination)
    temporary = None
    created = False
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', newline='', encoding='utf-8-sig', dir=target.parent,
            prefix='.storagescope-', suffix='.tmp', delete=False
        ) as output:
            temporary = Path(output.name)
            writer = csv.writer(output, delimiter=';')
            writer.writerow(HEADERS)
            for row in rows:
                if len(row) != len(HEADERS):
                    raise ValueError('Invalid inventory row width')
                writer.writerow([safe_csv_cell(cell) for cell in row])
        with temporary.open('rb') as source, target.open('xb') as output:
            created = True
            shutil.copyfileobj(source, output)
        return target
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
