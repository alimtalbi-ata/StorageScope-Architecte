"""Read-only regression timeline and architecture-review exports. Author: Abdelhalim Talbi."""
import csv
import io
import json
from datetime import datetime, timezone
from campaign_history_v526 import CampaignHistory
from campaign_alerts_v532 import alert_view
from campaign_report_v530 import _atomic_write

SEVERITY_RANK = {'critical': 0, 'warning': 1, 'info': 2}

def timeline(history, *, severity='all', limit=100, **filters):
    if severity not in ('all', *SEVERITY_RANK):
        raise ValueError('invalid severity')
    records = history.list(limit)
    # Read and validate the unfiltered global gate; never derive it from the UI filter.
    overall = history.report(limit)
    events = []
    for earlier, later in zip(records, records[1:]):
        view = alert_view(history, earlier['id'], later['id'], severity=severity, **filters)
        for alert in view['alerts']:
            events.append({'earlier_id': earlier['id'], 'later_id': later['id'],
                           'recorded_at': later['recorded_at'], 'severity': alert['severity'],
                           'code': alert['code'], 'count': alert['count'],
                           'evidence_ids': list(alert['evidence_ids']),
                           'coverage': alert['evidence_coverage'],
                           'earlier_sha256': earlier['sha256'], 'later_sha256': later['sha256']})
    groups = []
    for code in sorted({e['code'] for e in events}):
        subset = [e for e in events if e['code'] == code]
        groups.append({'code': code, 'severity': min((e['severity'] for e in subset), key=SEVERITY_RANK.get),
                       'occurrences': len(subset), 'total_count': sum(e['count'] for e in subset),
                       'partial_evidence': any(e['coverage'] != 'complete' for e in subset)})
    groups.sort(key=lambda x: (SEVERITY_RANK[x['severity']], x['code']))
    return {'schema': 'storagescope.regression-timeline.v5.33',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'campaign_count': len(records), 'compared_pairs': max(0, len(records)-1),
            'severity_filter': severity, 'category_filters': filters,
            'groups': groups, 'events': events, 'overall_gate': overall,
            'recommendation_only': True, 'production_activation': False,
            'filter_is_descriptive_only': True,
            'author': 'Abdelhalim Talbi'}

def export_timeline(history, destination, *, format='json', **kwargs):
    if format not in ('json', 'csv', 'md'):
        raise ValueError('unsupported export format')
    data = timeline(history, **kwargs)
    if format == 'json':
        content = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    elif format == 'csv':
        buf = io.StringIO(newline='')
        writer = csv.writer(buf)
        writer.writerow(['recorded_at','earlier_id','later_id','severity','code','count','coverage','evidence_ids','earlier_sha256','later_sha256'])
        for e in data['events']:
            writer.writerow([e[k] if k != 'evidence_ids' else json.dumps(e[k], ensure_ascii=False) for k in ('recorded_at','earlier_id','later_id','severity','code','count','coverage','evidence_ids','earlier_sha256','later_sha256')])
        content = buf.getvalue()
    elif format == 'md':
        def esc(x): return str(x).replace('\\','\\\\').replace('|','\\|').replace('\n',' ')
        content = ('# StorageScope v5.33 — Revue des régressions\n\n'
                   'Auteur : Abdelhalim Talbi\n\n'
                   f"Campagnes : {data['campaign_count']} ; comparaisons consécutives : {data['compared_pairs']}\n\n"
                   f"Politique globale : {esc(data['overall_gate']['selected_policy'])} — consultatif uniquement\n\n"
                   '| Date | Campagne A | Campagne B | Criticité | Type | Occurrences | Preuves |\n'
                   '|---|---|---|---|---|---:|---|\n')
        for e in data['events']:
            content += '| ' + ' | '.join(esc(e[k]) for k in ('recorded_at','earlier_id','later_id','severity','code','count','coverage')) + ' |\n'
        content += '\n**Lecture seule.** Les filtres n’affectent pas la politique globale.\n'
    else:
        raise ValueError('unsupported export format')
    _atomic_write(destination, content)
    return {'path': str(destination), 'format': format, 'event_count': len(data['events'])}
