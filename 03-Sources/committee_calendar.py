"""Read-only committee calendar and reminder drafts. Author: Abdelhalim Talbi."""
from datetime import date, timedelta
import hashlib
import json

class CommitteeCalendar:
    def __init__(self, planning):
        self.p = planning
        self.db = planning.db

    def snapshot(self, as_of=None, horizon_days=30):
        self.p.c.guard()
        today = date.fromisoformat(as_of) if as_of else date.today()
        if not isinstance(horizon_days, int) or isinstance(horizon_days,bool) or not 1 <= horizon_days <= 366:
            raise ValueError('horizon_days must be between 1 and 366')
        until = today + timedelta(days=horizon_days)
        meetings=[]
        for mid,title,when,status in self.db.execute('SELECT id,title,scheduled_at,status FROM meetings ORDER BY scheduled_at,id'):
            try: scheduled=date.fromisoformat(when[:10])
            except (ValueError,TypeError): continue
            if today <= scheduled <= until:
                meetings.append({'id':mid,'title':title,'date':scheduled.isoformat(),'status':status})
        followups=[]
        for fid,mid,did,owner,due,description in self.db.execute("SELECT id,meeting_id,decision_id,owner,due_date,description FROM meeting_followups WHERE status='OPEN' ORDER BY due_date,id"):
            due_day=date.fromisoformat(due)
            if due_day <= until:
                followups.append({'id':fid,'meeting_id':mid,'decision_id':did,'owner':owner,'due_date':due,'description':description,'overdue':due_day<today,'due_soon':today<=due_day<=today+timedelta(days=7)})
        return {'as_of':today.isoformat(),'until':until.isoformat(),'meetings':meetings,'followups':followups,'overdue_count':sum(f['overdue'] for f in followups)}

    def reminders(self, as_of=None, horizon_days=30):
        data=self.snapshot(as_of,horizon_days)
        grouped={}
        for item in data['followups']:
            grouped.setdefault(item['owner'],[]).append(item)
        result=[]
        for owner,items in sorted(grouped.items()):
            lines=[f"Bonjour {owner},",'',"Voici les actions de comité HLD/LLD à suivre :",'']
            for x in items:
                label='EN RETARD' if x['overdue'] else ('Échéance proche' if x['due_soon'] else 'À suivre')
                lines.append(f"- [{label}] {x['id']} — {x['description']} (décision {x['decision_id']}, échéance {x['due_date']})")
            lines+=['',"Merci de transmettre le statut et les références de preuve.","Message préparé, non envoyé automatiquement."]
            result.append({'owner':owner,'subject':'Suivi des actions HLD/LLD','body':'\n'.join(lines),'items':len(items)})
        return result

    def report(self, as_of=None, horizon_days=30):
        data=self.snapshot(as_of,horizon_days)
        lines=['# Calendrier et relances HLD/LLD',f"Période : {data['as_of']} → {data['until']}",'Auteur : Abdelhalim Talbi','','## Comités']
        lines += [f"- {x['date']} — {x['id']} : {x['title']} ({x['status']})" for x in data['meetings']]
        lines += ['', '## Actions ouvertes']
        lines += [f"- {'EN RETARD' if x['overdue'] else 'À suivre'} — {x['id']} / {x['owner']} / {x['due_date']} / {x['description']}" for x in data['followups']]
        lines += ['', '## Relances préparées (aucun envoi automatique)']
        for reminder in self.reminders(as_of,horizon_days):
            lines += ['',f"### {reminder['owner']}",'',reminder['body']]
        content='\n'.join(lines)+'\n'
        return content,hashlib.sha256(content.encode('utf-8')).hexdigest()
