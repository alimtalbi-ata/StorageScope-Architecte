"""Read-only timeline visualization model and verifiable architecture dossier. Author: Abdelhalim Talbi."""
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from campaign_timeline_v533 import timeline

COLORS = {'critical': '#b91c1c', 'warning': '#d97706', 'info': '#2563eb'}

def timeline_plot(report, width=900, height=270):
    """Generate deterministic plot positions without modifying policy decisions."""
    if type(width) is not int or type(height) is not int or width < 300 or height < 150:
        raise ValueError('invalid plot size')
    events = report['events']
    positions = []
    count = len(events)
    for i, event in enumerate(events):
        if event['severity'] not in COLORS or not isinstance(event['count'], int) or event['count'] < 0:
            raise ValueError('invalid event')
        x = 55 + (width - 105) * (i + .5) / max(1, count)
        y = height - 45 - min(event['count'], 20) / 20 * (height - 105)
        positions.append({'index': i, 'x': round(x, 2), 'y': round(y, 2),
                          'color': COLORS[event['severity']], 'count': event['count'],
                          'code': event['code'], 'later_id': event['later_id']})
    return {'width': width, 'height': height, 'points': positions,
            'read_only': True, 'production_activation': False}

def review_dossier(history, destination, **filters):
    """Atomically export JSON/Markdown/CSV and a SHA-256 manifest inside a ZIP."""
    from campaign_timeline_v533 import export_timeline
    destination = Path(destination)
    report = timeline(history, **filters)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.storagescope-review-', suffix='.zip', dir=destination.parent)
    os.close(fd)
    try:
        with tempfile.TemporaryDirectory() as workspace:
            folder = Path(workspace)
            artifacts = {}
            for fmt, filename in [('json','chronologie.json'),('csv','chronologie.csv'),('md','revue-architecture.md')]:
                export_timeline(history, folder / filename, format=fmt, **filters)
                artifacts[filename] = (folder / filename).read_bytes()
            from campaign_executive_v535 import executive_summary, decision_register
            summary = executive_summary(report)
            artifacts['synthese-executive.json'] = (json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
            artifacts['registre-decisions-modele.json'] = (json.dumps(decision_register(summary), ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
            artifacts['graphique.json'] = (json.dumps(timeline_plot(report), ensure_ascii=False, indent=2) + '\n').encode()
            manifest = {'schema': 'storagescope.architecture-review.v5.35',
                        'author': 'Abdelhalim Talbi', 'recommendation_only': True,
                        'production_activation': False,
                        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(artifacts.items())}}
            artifacts['MANIFEST-SHA256.json'] = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, content in sorted(artifacts.items()): archive.writestr(name, content)
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return {'path': str(destination), 'files': len(artifacts), 'events': len(report['events'])}
