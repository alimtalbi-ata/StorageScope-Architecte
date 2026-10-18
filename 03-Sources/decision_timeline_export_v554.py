"""Read-only filtered audit exports. Author: Abdelhalim Talbi."""
import csv
import io
import json
from pathlib import Path
from decision_timeline_presentation_v553 import timeline_presentation, STATUS


def filtered_timeline(store, ident, *, state='ALL', event_type='ALL'):
    if state != 'ALL' and state not in STATUS:
        raise ValueError('invalid state filter')
    if not isinstance(event_type, str) or not event_type or len(event_type) > 80:
        raise ValueError('invalid event filter')
    record = timeline_presentation(store, ident)  # verify full history before filtering
    rows = [r for r in record['events'] if (state == 'ALL' or r['state'] == state)
            and (event_type == 'ALL' or r['type'] == event_type)]
    return {**record, 'events': rows, 'filters': {'state': state, 'event_type': event_type},
            'total_events': len(record['events']), 'visible_events': len(rows)}


def export_timeline(store, ident, destination, *, format='json', state='ALL', event_type='ALL'):
    if format not in ('json', 'csv'):
        raise ValueError('unsupported format')
    data = filtered_timeline(store, ident, state=state, event_type=event_type)
    if format == 'json':
        content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    else:
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(['decision_id', 'audit_head', 'sequence', 'type', 'label', 'state', 'verdict', 'actor'])
        for event in data['events']:
            writer.writerow([ident, data['audit_head'], event['sequence'], event['type'],
                             event['label'], event['state'], event.get('qualification_verdict') or '',
                             event.get('actor') or ''])
        content = stream.getvalue()
    from campaign_report_v530 import _atomic_write
    _atomic_write(Path(destination), content)
    return data
