"""Pure presentation model for governance UI; no production action. Author: Abdelhalim Talbi."""
from collections import Counter

PRIORITIES = {'P1': ('Urgent', '#a62d37'), 'P2': ('À traiter', '#a96912'), 'P3': ('Suivi', '#246e56')}

def visual_summary(result):
    """Build display-only indicators from a previously verified workspace result."""
    if not isinstance(result, dict) or result.get('consistency_verified') is not True or result.get('production_activation') is not False:
        raise ValueError('unverified workspace')
    sheets = result.get('decision_sheets')
    if not isinstance(sheets, list): raise ValueError('invalid decisions')
    ids = [x['id'] for x in sheets]
    if len(set(ids)) != len(ids): raise ValueError('duplicate decision')
    counts = Counter(x['priority'] for x in sheets)
    if any(p not in PRIORITIES for p in counts): raise ValueError('unknown priority')
    overdue = sum(x.get('deadline_state') == 'overdue' for x in sheets)
    review = sum(bool(x.get('requires_human_review')) for x in sheets)
    return {'total':len(sheets), 'overdue':overdue, 'human_review':review,
            'priorities':{p:counts[p] for p in PRIORITIES},
            'legend':{p:{'label':label,'color':color} for p,(label,color) in PRIORITIES.items()},
            'audit_head':result['audit_head'], 'production_activation':False}

def evidence_navigation(sheet):
    """Read-only evidence references; presence is not verification of sufficiency."""
    if not isinstance(sheet,dict) or not sheet.get('id'): raise ValueError('invalid sheet')
    return {'decision_id':sheet['id'], 'reference':sheet.get('evidence_reference') or '',
            'linked_alerts':sheet.get('linked_events',0), 'sufficiency_verified':False,
            'message':'Référence informative : vérifier la pertinence et la suffisance des preuves.'}
