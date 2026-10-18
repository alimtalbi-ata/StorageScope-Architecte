"""Conservative cross-campaign stability audit. Author: Abdelhalim Talbi."""
import math
from statistics import median
from collections import defaultdict
from benchmark_analysis_v524 import summarize

def audit_campaigns(campaigns, min_campaigns=3, max_outlier_fraction=.15, max_drift=.10):
    if not isinstance(campaigns,(list,tuple)) or isinstance(min_campaigns,bool) or not isinstance(min_campaigns,int) or min_campaigns<2:
        raise ValueError('invalid campaigns/config')
    if not (0<=max_outlier_fraction<1 and 0<=max_drift<1):
        raise ValueError('invalid limits')
    seen=set(); reports=[]; by_category=defaultdict(list); outliers=0; observations=0
    for campaign in campaigns:
        if not isinstance(campaign,dict) or not isinstance(campaign.get('id'),str) or not campaign['id'] or campaign['id'] in seen:
            raise ValueError('invalid campaign id')
        seen.add(campaign['id'])
        pairs=campaign.get('pairs')
        report=summarize(pairs)
        reports.append({'id':campaign['id'],'reason':report['reason'],'selected_policy':report['selected_policy']})
        for cat in report['categories']:
            key=(cat['nodes'],cat['edits'],cat['spacing'])
            by_category[key].append(cat['median_gain'])
            # Descriptive Tukey fence; never remove observations from the safety gate.
            vals=sorted((p['baseline_seconds']-p['candidate_seconds'])/p['baseline_seconds'] for p in pairs if (p['nodes'],p['edits'],p['spacing'])==key)
            if len(vals)>=4:
                lower=vals[:len(vals)//2];upper=vals[(len(vals)+1)//2:]
                q1=median(lower);q3=median(upper);iqr=q3-q1
                outliers+=sum(v<q1-1.5*iqr or v>q3+1.5*iqr for v in vals)
            observations+=len(vals)
    sufficient=len(campaigns)>=min_campaigns
    stable_categories=all(len(v)==len(campaigns) and max(v)-min(v)<=max_drift for v in by_category.values()) and bool(by_category)
    outlier_fraction=outliers/observations if observations else 0
    all_pass=all(r['selected_policy']=='candidate_measured' for r in reports)
    if not sufficient: reason='insufficient_campaigns'
    elif not stable_categories: reason='cross_campaign_drift_or_missing_category'
    elif outlier_fraction>max_outlier_fraction: reason='excessive_outliers'
    elif not all_pass: reason='campaign_gate_rejected'
    else: reason='candidate_stable_across_campaigns'
    return {'selected_policy':'candidate_measured' if reason=='candidate_stable_across_campaigns' else 'default',
        'reason':reason,'recommendation_only':True,'production_activation':False,
        'campaign_count':len(campaigns),'outliers':outliers,'observations':observations,
        'outlier_fraction':outlier_fraction,'categories':len(by_category),'campaigns':reports}
