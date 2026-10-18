"""Standalone Windows-friendly governance committee viewer. Author: Abdelhalim Talbi."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from decision_governance_v537 import GovernanceStore
from decision_committee_v538 import committee_dashboard, export_committee
from decision_integrity_v540 import decision_detail
from decision_workspace_v542 import workspace


def launch(db_path='architecture-decisions.sqlite'):
    store=GovernanceStore(db_path)
    root=tk.Tk();root.title('StorageScope v5.42 | Espace de gouvernance');root.geometry('1050x650')
    top=ttk.Frame(root,padding=12);top.pack(fill='x')
    owner=tk.StringVar();status=tk.StringVar(value='all');deadline=tk.StringVar(value='all');search=tk.StringVar()
    ttk.Label(top,text='Responsable').grid(row=0,column=0,sticky='w')
    ttk.Entry(top,textvariable=owner,width=22).grid(row=1,column=0,padx=5)
    ttk.Label(top,text='Statut').grid(row=0,column=1,sticky='w')
    ttk.Combobox(top,textvariable=status,state='readonly',values=('all','OPEN','IN_REVIEW','APPROVED','REJECTED','CLOSED'),width=17).grid(row=1,column=1,padx=5)
    ttk.Label(top,text='Échéance').grid(row=0,column=2,sticky='w')
    ttk.Combobox(top,textvariable=deadline,state='readonly',values=('all','overdue','due_today','upcoming','closed'),width=17).grid(row=1,column=2,padx=5)
    ttk.Label(top,text='Recherche').grid(row=0,column=3,sticky='w')
    ttk.Entry(top,textvariable=search,width=23).grid(row=1,column=3,padx=5)
    summary=tk.StringVar(value='');ttk.Label(root,textvariable=summary,padding=10).pack(fill='x')
    cols=('priority','id','subject','owner','status','due_date','linked_events')
    tree=ttk.Treeview(root,columns=cols,show='headings',height=19)
    for c in cols:tree.heading(c,text=c);tree.column(c,width=115 if c!='subject' else 230)
    tree.pack(fill='both',expand=True,padx=12,pady=8)
    def filters():return {'owner':owner.get().strip() or None,'status':status.get(),'deadline':deadline.get()}
    def refresh():
        try:
            data=workspace(store,query=search.get(),**filters())
            tree.delete(*tree.get_children())
            for a in data['decision_sheets']:tree.insert('', 'end', iid=a['id'], values=[a[c] for c in cols])
            summary.set(f"Affichées : {data['visible_kpis']['count']} | P1 : {data['visible_kpis']['p1']} | P2 : {data['visible_kpis']['p2']} | Revue : {data['visible_kpis']['needs_review']} | Retards globaux : {data['global_kpis']['overdue']} | Audit : {data['audit_head'][:16]}…")
        except (ValueError,KeyError) as exc:messagebox.showerror('Validation',str(exc))
    def export(fmt):
        try:
            path=filedialog.asksaveasfilename(defaultextension='.'+fmt,filetypes=[(fmt.upper(),'*.'+fmt)])
            if path:export_committee(store,path,format=fmt,**filters())
        except (ValueError,OSError) as exc:messagebox.showerror('Export',str(exc))
    def show_detail(_event=None):
        selected=tree.selection()
        if not selected:return
        try:
            data=decision_detail(store,selected[0],**filters())
            popup=tk.Toplevel(root);popup.title('Fiche vérifiée | '+selected[0]);popup.geometry('850x560')
            viewer=tk.Text(popup,wrap='word');viewer.pack(fill='both',expand=True,padx=10,pady=10)
            import json
            viewer.insert('1.0',json.dumps(data,ensure_ascii=False,indent=2));viewer.configure(state='disabled')
        except (ValueError,KeyError) as exc:messagebox.showerror('Cohérence',str(exc))
    tree.bind('<Double-1>',show_detail)
    ttk.Button(top,text='Fiche détaillée',command=show_detail).grid(row=2,column=0,pady=5)
    ttk.Button(top,text='Actualiser',command=refresh).grid(row=2,column=3,padx=10)
    for idx,fmt in enumerate(('md','csv','json'),start=4):
        ttk.Button(top,text='Exporter '+fmt.upper(),command=lambda f=fmt:export(f)).grid(row=1,column=idx,padx=3)
    refresh();root.mainloop()

if __name__=='__main__':launch()
