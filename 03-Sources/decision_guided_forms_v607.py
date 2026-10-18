"""Guided, validated Tk decision forms. Author: Abdelhalim Talbi."""
from datetime import date

STATUSES=('IN_REVIEW','APPROVED','REJECTED','CLOSED')

def validate_decision(values):
    if not isinstance(values,dict):raise ValueError('Formulaire invalide')
    required=('ident','subject','owner','due_date','evidence_reference')
    cleaned={key:str(values.get(key,'')).strip() for key in required}
    if any(not cleaned[key] for key in required):raise ValueError('Tous les champs sont obligatoires')
    try:date.fromisoformat(cleaned['due_date'])
    except ValueError as exc:raise ValueError('Échéance attendue au format AAAA-MM-JJ') from exc
    return cleaned

def validate_transition(values):
    if not isinstance(values,dict):raise ValueError('Formulaire invalide')
    cleaned={key:str(values.get(key,'')).strip() for key in ('status','actor','rationale','approval')}
    if cleaned['status'] not in STATUSES:raise ValueError('Statut invalide')
    if not cleaned['actor'] or not cleaned['rationale']:raise ValueError('Auteur et justification obligatoires')
    if cleaned['status']=='APPROVED' and not cleaned['approval']:raise ValueError('Validation humaine requise pour APPROVED')
    cleaned['approval']=cleaned['approval'] or None
    return cleaned

def _dialog(parent,title,fields,validator,choices=None):
    import tkinter as tk
    from tkinter import ttk,messagebox
    win=tk.Toplevel(parent);win.title(title);win.transient(parent);win.resizable(False,False)
    body=ttk.Frame(win,padding=16);body.pack(fill='both',expand=True)
    ttk.Label(body,text=title,font=('Segoe UI',13,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,12))
    vars={}
    for row,(key,label,default) in enumerate(fields,1):
        ttk.Label(body,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=5)
        var=tk.StringVar(value=default);vars[key]=var
        if choices and key in choices:
            widget=ttk.Combobox(body,textvariable=var,values=choices[key],state='readonly',width=38)
        else:widget=ttk.Entry(body,textvariable=var,width=41)
        widget.grid(row=row,column=1,sticky='ew',pady=5)
        if row==1:widget.focus_set()
    ttk.Label(body,text='Les champs requis sont contrôlés avant enregistrement.',foreground='#555').grid(row=len(fields)+1,column=0,columnspan=2,sticky='w',pady=(8,5))
    error=tk.StringVar(value='')
    ttk.Label(body,textvariable=error,foreground='#a52222',wraplength=410).grid(row=len(fields)+2,column=0,columnspan=2,sticky='w')
    result=[None]
    def save():
        try:validated=validator({key:var.get() for key,var in vars.items()})
        except ValueError as exc:
            error.set(str(exc));win.bell();return
        result[0]=validated
        win.destroy()
    buttons=ttk.Frame(body);buttons.grid(row=len(fields)+3,column=0,columnspan=2,sticky='e',pady=(8,0))
    ttk.Button(buttons,text='Annuler',command=win.destroy).pack(side='left',padx=5)
    ttk.Button(buttons,text='Valider',command=save).pack(side='left')
    win.bind('<Escape>',lambda event:win.destroy());win.bind('<Return>',lambda event:save())
    win.grab_set();parent.wait_window(win)
    return result[0]

def guided_decision_form(parent,*,title='Nouvelle décision'):
    return _dialog(parent,title,[('ident','Identifiant *',''),('subject','Sujet *',''),('owner','Responsable *',''),('due_date','Échéance AAAA-MM-JJ *',''),('evidence_reference','Référence de preuve *','')],validate_decision)

def guided_transition_form(parent):
    return _dialog(parent,'Changer le statut',[('status','Nouveau statut *','IN_REVIEW'),('actor','Auteur *',''),('rationale','Justification *',''),('approval','Référence de validation (si approuvée)','')],validate_transition,{'status':STATUSES})


QUALIFICATION_LABELS = {
    'traceability': 'Traçabilité des preuves',
    'relevance': 'Pertinence des preuves',
    'integrity': 'Intégrité des preuves',
    'coverage': 'Couverture des exigences',
}

def validate_qualification(values):
    from decision_qualification_v547 import CRITERIA, VERDICTS
    if not isinstance(values,dict): raise ValueError('Formulaire invalide')
    actor=str(values.get('actor','')).strip()
    verdict=str(values.get('verdict','')).strip()
    rationale=str(values.get('rationale','')).strip()
    criteria=values.get('criteria')
    if not actor or not rationale: raise ValueError('Réviseur et justification obligatoires')
    if verdict not in VERDICTS: raise ValueError('Verdict de qualification invalide')
    if not isinstance(criteria,dict) or set(criteria)!=set(CRITERIA) or any(type(v) is not bool for v in criteria.values()):
        raise ValueError('Chaque critère doit être évalué explicitement')
    if verdict=='ACCEPT' and not all(criteria.values()):
        raise ValueError('Impossible d’accepter des critères non satisfaits')
    return {'actor':actor,'verdict':verdict,'criteria':dict(criteria),'rationale':rationale}


def validate_committee(values):
    from decision_committee_resolution_v558 import VERDICTS
    if not isinstance(values,dict): raise ValueError('Formulaire invalide')
    result={key:str(values.get(key,'')).strip() for key in ('actor','meeting_date','verdict','rationale')}
    if not result['actor'] or not result['rationale']: raise ValueError('Acteur et justification obligatoires')
    try: result['meeting_date']=date.fromisoformat(result['meeting_date']).isoformat()
    except ValueError as exc: raise ValueError('Date de séance invalide (AAAA-MM-JJ)') from exc
    if result['verdict'] not in VERDICTS: raise ValueError('Décision de comité invalide')
    return result


def guided_committee_form(parent):
    return _dialog(parent,'Décision du comité',[
        ('actor','Acteur humain *',''),('meeting_date','Date de séance *',date.today().isoformat()),
        ('verdict','Verdict *','DEFER'),('rationale','Justification *','')],
        validate_committee,{'verdict':('APPROVE','REJECT','DEFER')})


def guided_qualification_form(parent):
    import tkinter as tk
    from tkinter import ttk,messagebox
    from decision_qualification_v547 import CRITERIA,VERDICTS
    win=tk.Toplevel(parent);win.title('Qualification des preuves');win.transient(parent);win.resizable(False,False)
    body=ttk.Frame(win,padding=16);body.pack(fill='both',expand=True)
    ttk.Label(body,text='Qualification humaine des preuves',font=('Segoe UI',13,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,10))
    actor=tk.StringVar();verdict=tk.StringVar(value='NEEDS_MORE_EVIDENCE');rationale=tk.StringVar()
    for idx,(label,var) in enumerate((('Réviseur *',actor),('Justification *',rationale)),1):
        ttk.Label(body,text=label).grid(row=idx,column=0,sticky='w',pady=4)
        entry=ttk.Entry(body,textvariable=var,width=43)
        entry.grid(row=idx,column=1,sticky='ew',pady=4)
        if idx==1:entry.focus_set()
    ttk.Label(body,text='Verdict *').grid(row=3,column=0,sticky='w',pady=4)
    ttk.Combobox(body,textvariable=verdict,values=VERDICTS,state='readonly',width=40).grid(row=3,column=1,sticky='ew',pady=4)
    checks={}
    for idx,key in enumerate(CRITERIA,4):
        checks[key]=tk.BooleanVar(value=False)
        ttk.Checkbutton(body,text=QUALIFICATION_LABELS.get(key,key),variable=checks[key]).grid(row=idx,column=0,columnspan=2,sticky='w',pady=3)
    ttk.Label(body,text='Cochez uniquement les critères réellement vérifiés.',foreground='#555').grid(row=8,column=0,columnspan=2,sticky='w',pady=(8,4))
    error=tk.StringVar(value='')
    ttk.Label(body,textvariable=error,foreground='#a52222',wraplength=420).grid(row=9,column=0,columnspan=2,sticky='w')
    result=[None]
    def save():
        try:validated=validate_qualification({'actor':actor.get(),'verdict':verdict.get(),'rationale':rationale.get(),'criteria':{key:var.get() for key,var in checks.items()}})
        except ValueError as exc:
            error.set(str(exc));win.bell();return
        result[0]=validated
        win.destroy()
    buttons=ttk.Frame(body);buttons.grid(row=10,column=0,columnspan=2,sticky='e',pady=8)
    ttk.Button(buttons,text='Annuler',command=win.destroy).pack(side='left',padx=5)
    ttk.Button(buttons,text='Valider',command=save).pack(side='left')
    win.bind('<Escape>',lambda event:win.destroy())
    win.bind('<Control-Return>',lambda event:save())
    win.grab_set();parent.wait_window(win)
    return result[0]
