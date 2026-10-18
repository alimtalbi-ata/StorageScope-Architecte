"""StorageScope v6.20 read-only governance HTML report (no external assets)."""
from __future__ import annotations
import argparse, datetime as dt, html, json
from pathlib import Path
from inventory_quality_v618 import inspect_inventory
from inventory_reconcile_v619 import reconcile

def build_report(records, now=None):
    quality = inspect_inventory(records, now=now)
    reconciliation = reconcile(records)
    return {'schema':'storagescope.governance.v1','quality':quality,'reconciliation':reconciliation,
            'review_required':reconciliation['candidate_count'], 'destructive_changes':0}

def render_html(report):
    q, r = report['quality'], report['reconciliation']
    esc=lambda x:html.escape(str(x), quote=True)
    rows=[]
    for issue in q['issues']:
        rows.append('<tr><td>'+esc(issue.get('index',''))+'</td><td>'+esc(issue.get('code',''))+'</td><td>'+esc(issue.get('field',issue.get('detail','')))+'</td></tr>')
    matches=[]
    for candidate in r['candidates']:
        matches.append('<tr><td>'+esc(', '.join(map(str,candidate['indices'])))+'</td><td>'+esc(', '.join(candidate['identity_evidence']))+'</td><td>'+esc(len(candidate['conflicts']))+'</td><td>REVIEW_REQUIRED</td></tr>')
    return '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>StorageScope | Gouvernance v6.20</title><style>body{font:16px system-ui,sans-serif;margin:0;background:#f4f6fa;color:#15253b}header{background:#152b49;color:white;padding:24px 5%}main{max-width:1200px;margin:auto;padding:24px}section{background:white;padding:20px;border-radius:12px;margin-bottom:20px;box-shadow:0 2px 10px #14243b15}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.stat{padding:16px;background:#eaf0f8;border-radius:10px}.stat strong{font-size:2rem;display:block}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #dce3ed;padding:10px}th{background:#edf2f8}input{width:100%;box-sizing:border-box;padding:10px;margin-bottom:12px}small{color:#506178}.scroll{overflow:auto}</style></head><body><header><h1>StorageScope — Gouvernance</h1><p>Rapport local en lecture seule · v6.20 · Abdelhalim Talbi</p></header><main><section class="stats"><div class="stat">Qualité<strong>'''+esc(q['score'])+'''%</strong></div><div class="stat">Enregistrements<strong>'''+esc(q['total'])+'''</strong></div><div class="stat">Anomalies<strong>'''+esc(q['issue_count'])+'''</strong></div><div class="stat">Rapprochements à valider<strong>'''+esc(r['candidate_count'])+'''</strong></div></section><section><h2>Anomalies de qualité</h2><input aria-label="Filtrer les anomalies" placeholder="Rechercher dans les anomalies" oninput="filterTable(this,'issues')"><div class="scroll"><table id="issues"><thead><tr><th>Index</th><th>Code</th><th>Détail</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div></section><section><h2>Candidats à réconcilier</h2><p><small>Aucune fusion automatique : validation humaine obligatoire.</small></p><input aria-label="Filtrer les rapprochements" placeholder="Rechercher dans les rapprochements" oninput="filterTable(this,'matches')"><div class="scroll"><table id="matches"><thead><tr><th>Index</th><th>Preuves d'identité</th><th>Conflits</th><th>Action</th></tr></thead><tbody>'''+''.join(matches)+'''</tbody></table></div></section></main><script>function filterTable(el,id){const v=el.value.toLocaleLowerCase();document.querySelectorAll('#'+id+' tbody tr').forEach(row=>row.hidden=!row.textContent.toLocaleLowerCase().includes(v))}</script></body></html>'''

def main(argv=None):
    p=argparse.ArgumentParser(description='Generate offline read-only governance dashboard')
    p.add_argument('input',type=Path);p.add_argument('--html',type=Path,required=True);p.add_argument('--json',type=Path)
    a=p.parse_args(argv)
    report=build_report(json.loads(a.input.read_text(encoding='utf-8')))
    a.html.write_text(render_html(report),encoding='utf-8')
    if a.json:a.json.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if not report['quality']['issue_count'] and not report['reconciliation']['invalid_records'] else 1
if __name__=='__main__':raise SystemExit(main())
