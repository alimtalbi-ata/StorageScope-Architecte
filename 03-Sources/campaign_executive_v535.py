"""Fail-closed executive architecture review; recommendations never authorize changes.
Author: Abdelhalim Talbi.
"""
from collections import Counter
from datetime import datetime, timezone

PRIORITY = {'critical': 0, 'warning': 1, 'info': 2}

def executive_summary(report):
    events = report['events']
    groups = report['groups']
    gate = report['overall_gate']
    if not isinstance(events, list) or not isinstance(groups, list) or not isinstance(gate, dict):
        raise ValueError('invalid architecture review')
    counts = Counter()
    for event in events:
        if event['severity'] not in PRIORITY or type(event['count']) is not int or event['count'] < 0:
            raise ValueError('invalid event')
        counts[event['severity']] += event['count']
    actions = []
    for group in sorted(groups, key=lambda g: (PRIORITY[g['severity']], -g['total_count'], g['code'])):
        if group['severity'] not in PRIORITY or type(group['total_count']) is not int or group['total_count'] < 0:
            raise ValueError('invalid group')
        actions.append({'priority': 'P1' if group['severity']=='critical' else 'P2' if group['severity']=='warning' else 'P3',
                        'type': group['code'], 'occurrences': group['total_count'],
                        'action': 'Analyser les preuves et confirmer la cause avant décision',
                        'proof_status': 'incomplete' if group['partial_evidence'] else 'reported_complete',
                        'decision_status': 'pending_human_review'})
    if not actions:
        actions.append({'priority':'P3','type':'no_alerts_in_scope','occurrences':0,
                        'action':'Vérifier la couverture des campagnes et des filtres avant toute conclusion',
                        'proof_status':'not_applicable','decision_status':'pending_human_review'})
    return {'schema':'storagescope.executive-review.v5.35', 'author':'Abdelhalim Talbi',
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'campaign_count':report['campaign_count'], 'compared_pairs':report['compared_pairs'],
            'severity_filter':report['severity_filter'], 'counts_by_severity':dict(counts),
            'incomplete_evidence_events':sum(e['coverage'] != 'complete' for e in events),
            'global_gate':gate, 'priority_actions':actions, 'recommendation_only':True,
            'production_activation':False, 'filter_is_descriptive_only':True,
            'conclusion':'Revue humaine requise; aucune autorisation de mise en production.'}

def decision_register(summary):
    return {'schema':'storagescope.decision-register-template.v5.35',
            'author':'Abdelhalim Talbi','entries':[
                {'id':f'ADR-{i:03}', 'priority':a['priority'], 'subject':a['type'],
                 'proposed_action':a['action'], 'decision':'UNDECIDED',
                 'owner':None,'due_date':None,'rationale':None,'evidence_reference':None,
                 'approval':None} for i,a in enumerate(summary['priority_actions'],1)],
            'template_only':True,'recommendation_only':True,'production_activation':False}
