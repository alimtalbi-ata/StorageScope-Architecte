import time
from graph_diagnostics import diagnose_routes
from graph_prepare import prepare_graph
from graph_freshness import database_fingerprint
from graph_viewport import visible_cards, visible_routes
from graph_spatial import card_index, route_index
"""StorageScope v4.57 governance desktop companion. Author: Abdelhalim Talbi."""
import sqlite3
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from governance import Governance
from governance_extensions import overview, export_snapshot
from traceability import Traceability
from dashboard import dashboard_snapshot, graph_model
from fast_dashboard import summary_metrics, decision_graph, bounded_rows, find_decisions
from graph_layout import layout_nodes, filter_nodes, grouped_nodes, layout_grouped, orthogonal_routes, minimap_geometry, routed_connections, minimap_scroll_fraction, minimap_viewport, route_obstacles, obstacle_aware_routes, optimized_obstacle_routes, scalable_obstacle_routes, route_interference
from graph_export import export_svg, export_png
from route_scheduler import RouteScheduler
from committee import Committees
from planning import Planning
from committee_calendar import CommitteeCalendar
from month_view import MonthView
from portfolio import portfolio_snapshot
from cursor_pagination import decision_page
from async_portfolio import load_portfolio_readonly

class GovernanceWindow(tk.Tk):
    def __init__(self, database=None):
        super().__init__()
        self.title('StorageScope · Gouvernance HLD/LLD · v4.91')
        self.geometry('1020x670')
        self.dbpath = Path(database or Path.home()/'.storagescope'/'governance.sqlite3')
        self.dbpath.parent.mkdir(parents=True, exist_ok=True)
        self.g = Governance(self.dbpath)
        self.trace = Traceability(self.g)
        self.committees = Committees(self.g)
        self.planning = Planning(self.committees)
        self.calendar = CommitteeCalendar(self.planning)
        self.month_view = MonthView(self.calendar)
        self.protocol('WM_DELETE_WINDOW', self.shutdown)
        self.configure(bg='#f3f6fb')
        head=ttk.Frame(self, padding=15); head.pack(fill='x')
        ttk.Label(head,text='Gouvernance HLD / LLD',font=('Segoe UI',19,'bold')).pack(side='left')
        ttk.Button(head,text='Exporter Markdown',command=self.export).pack(side='right',padx=5)
        ttk.Button(head,text='Vérifier audit',command=self.audit).pack(side='right',padx=5)
        self.summary=ttk.Label(self,text='',font=('Segoe UI',11,'bold'),padding=8)
        self.summary.pack(fill='x',padx=15)
        book=ttk.Notebook(self);book.pack(fill='both',expand=True,padx=15,pady=8)
        self.dec=ttk.Frame(book,padding=10);self.res=ttk.Frame(book,padding=10)
        book.add(self.dec,text='Décisions / ADR');book.add(self.res,text='Réserves')
        self.decision_table=self.table(self.dec,('ID','Titre','État','Auteur','Approbateur'))
        self.reservation_table=self.table(self.res,('ID','Décision','Description','Bloquante','État','Responsable'))
        self.art = ttk.Frame(book,padding=10); book.add(self.art,text="Traçabilité / Clôture")
        self.dashboard = ttk.Frame(book,padding=10); book.insert(0,self.dashboard,text="Vue gouvernance")
        self.dashboard_form()
        self.portfolio_tab=ttk.Frame(book,padding=10);book.insert(1,self.portfolio_tab,text="Pilotage transversal")
        self.portfolio_form()
        self.meet = ttk.Frame(book,padding=10);book.add(self.meet,text='Comités / Planning')
        self.month_tab=ttk.Frame(book,padding=10);book.add(self.month_tab,text='Calendrier mensuel')
        self.month_form()
        self.decision_form();self.reservation_form();self.artifact_form();self.meeting_form();self.planning_form();self.refresh()
        ttk.Label(self,text='Auteur : Abdelhalim Talbi  ·  Les identités saisies ne sont pas authentifiées dans ce module.',foreground='#755d19').pack(pady=7)

    def portfolio_form(self):
        bar=ttk.Frame(self.portfolio_tab);bar.pack(fill='x',pady=5)
        ttk.Label(bar,text='Filtrer responsable / auteur :').pack(side='left')
        self.portfolio_owner=tk.StringVar()
        ttk.Entry(bar,textvariable=self.portfolio_owner,width=26).pack(side='left',padx=8)
        ttk.Label(bar,text='Recherche :').pack(side='left')
        self.portfolio_query=tk.StringVar()
        search=ttk.Entry(bar,textvariable=self.portfolio_query,width=22);search.pack(side='left',padx=4)
        search.bind('<Return>',lambda event:self.refresh_portfolio())
        self.portfolio_priority=tk.StringVar(value='TOUTES')
        ttk.Combobox(bar,textvariable=self.portfolio_priority,values=('TOUTES','CRITIQUE','ATTENTION','NORMAL'),state='readonly',width=11).pack(side='left',padx=4)
        self.portfolio_sort=tk.StringVar(value='priority')
        ttk.Combobox(bar,textvariable=self.portfolio_sort,values=('priority','id','status','overdue'),state='readonly',width=10).pack(side='left',padx=4)
        ttk.Button(bar,text='Actualiser',command=self.refresh_portfolio).pack(side='left')
        self.cursor_mode=tk.BooleanVar(value=False)
        ttk.Checkbutton(bar,text='Navigation rapide (ID)',variable=self.cursor_mode,command=self.reset_portfolio_navigation).pack(side='left',padx=4)
        self._portfolio_generation=0
        self._portfolio_results=queue.Queue()
        self._portfolio_polling=False
        self._portfolio_busy=False
        self._portfolio_cache={}
        self._portfolio_revision=None
        self.cursor_history=[None]
        self.cursor_index=0
        self.portfolio_offset=0
        self.portfolio_page_size=50
        ttk.Button(bar,text='◀ Précédent',command=lambda:self.portfolio_page(-1)).pack(side='left',padx=3)
        ttk.Button(bar,text='Suivant ▶',command=lambda:self.portfolio_page(1)).pack(side='left',padx=3)
        self.portfolio_summary=ttk.Label(self.portfolio_tab,text='')
        self.portfolio_summary.pack(anchor='w',pady=6)
        self.portfolio_table=self.table(self.portfolio_tab,('Priorité','Décision','État','Réserves','Actions','Retards','Comités'))
        self.portfolio_table.bind('<<TreeviewSelect>>',self.portfolio_select)
        ttk.Label(self.portfolio_tab,text='Double-cliquer sur une ligne pour afficher le graphe des dépendances.').pack(anchor='w')
        self.portfolio_table.bind('<Double-1>',self.portfolio_open)

    def reset_portfolio_navigation(self):
        self.portfolio_offset=0
        self.cursor_history=[None]
        self.cursor_index=0
        self.refresh_portfolio()

    def _poll_portfolio_results(self):
        try:
            while True:
                generation, result, error = self._portfolio_results.get_nowait()
                if generation != self._portfolio_generation:
                    continue
                if error is not None:
                    self._portfolio_busy=False
                    self.portfolio_summary.configure(text='Navigation indisponible : '+error)
                    continue
                self._portfolio_busy=False
                if result.get('cache_key') is not None:
                    if len(self._portfolio_cache)>=12: self._portfolio_cache.clear()
                    self._portfolio_cache[result['cache_key']]=result['data']
                self.portfolio_table.delete(*self.portfolio_table.get_children())
                if result['mode']=='cursor':
                    data=result['data']
                    for item in data['items']:
                        self.portfolio_table.insert('', 'end', iid=item['id'], values=('-',item['id'],item['status'],'-','-','-','-'))
                    self.cursor_next=data['next_cursor']
                    self.portfolio_summary.configure(text=f"Navigation rapide · page {self.cursor_index+1} · {len(data['items'])} décisions · Suite : {'oui' if data['has_next'] else 'non'}")
                else:
                    data=result['data']
                    for item in data['items']:
                        self.portfolio_table.insert('', 'end',iid=item['id'],values=(item['priority'],item['id'],item['status'],len(item['blockers']),len(item['actions']),item['overdue_count'],', '.join(item['committees'])))
                    self.portfolio_total=data['total_matches']
                    m=data['metrics']
                    self.portfolio_summary.configure(text=f"Résultats : {len(data['items'])}/{data['total_matches']} (page {self.portfolio_offset//self.portfolio_page_size+1}) | Décisions : {m['decisions']} | Critiques : {m['critical']} | À valider : {m['pending']} | Retards : {m['overdue']}")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(80, self._poll_portfolio_results)

    def _start_portfolio_worker(self, mode, parameters):
        self._portfolio_generation += 1
        generation=self._portfolio_generation
        revision=(self.g.db.total_changes,self.g.db.execute('PRAGMA data_version').fetchone()[0])
        if revision != self._portfolio_revision:
            self._portfolio_cache.clear()
            self._portfolio_revision=revision
        cache_key=(mode,tuple(sorted(parameters.items())),revision)
        if cache_key in self._portfolio_cache:
            self._portfolio_results.put((generation,{'mode':mode,'data':self._portfolio_cache[cache_key]},None))
            if not self._portfolio_polling:
                self._portfolio_polling=True
                self.after(80,self._poll_portfolio_results)
            return
        self._portfolio_busy=True
        self.portfolio_summary.configure(text='Chargement en arrière-plan…')
        if not self._portfolio_polling:
            self._portfolio_polling=True
            self.after(80,self._poll_portfolio_results)
        path=str(self.dbpath)
        def worker():
            try:
                data=load_portfolio_readonly(path,mode=mode,**parameters)
                self._portfolio_results.put((generation,{'mode':mode,'data':data,'cache_key':cache_key},None))
            except Exception as exc:
                self._portfolio_results.put((generation,None,str(exc)))
        threading.Thread(target=worker,daemon=True,name='storagescope-portfolio-reader').start()

    def _async_cursor_page(self):
        self._start_portfolio_worker('cursor',dict(limit=self.portfolio_page_size,cursor=self.cursor_history[self.cursor_index]))

    def refresh_portfolio(self):
        try:
            if self.cursor_mode.get():
                if any((self.portfolio_owner.get().strip(),self.portfolio_query.get().strip())) or self.portfolio_priority.get()!='TOUTES' or self.portfolio_sort.get()!='id':
                    self._portfolio_generation+=1
                    self.portfolio_summary.configure(text='Navigation rapide : vider les filtres et sélectionner le tri ID.')
                    return
                self._async_cursor_page()
                return
            params=dict(owner=self.portfolio_owner.get(),query=self.portfolio_query.get(),priority=self.portfolio_priority.get(),sort=self.portfolio_sort.get(),limit=self.portfolio_page_size,offset=self.portfolio_offset)
            self._start_portfolio_worker('filtered',params)
        except Exception as exc:
            self.portfolio_summary.configure(text='Pilotage indisponible : '+str(exc))

    def portfolio_page(self,direction):
        if self.cursor_mode.get():
            if direction<0 and self.cursor_index>0:
                self.cursor_index-=1
            elif direction>0 and getattr(self,'cursor_next',None):
                self.cursor_history=self.cursor_history[:self.cursor_index+1]+[self.cursor_next]
                self.cursor_index+=1
            else:return
            self.refresh_portfolio()
            return
        new_offset=max(0,self.portfolio_offset+direction*self.portfolio_page_size)
        if direction>0 and new_offset>=getattr(self,'portfolio_total',0): return
        self.portfolio_offset=new_offset
        self.refresh_portfolio()

    def portfolio_select(self,event=None):
        selection=self.portfolio_table.selection()
        if selection:self.selected_decision.set(selection[0])

    def portfolio_open(self,event=None):
        self.portfolio_select()
        self.select_graph_decision(self.selected_decision.get())
        self.portfolio_tab.master.select(self.dashboard)

    def table(self,parent,columns):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
        t=ttk.Treeview(frame,columns=columns,show='headings',height=13,selectmode='browse')
        for col in columns:t.heading(col,text=col);t.column(col,width=150,stretch=True)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=t.yview);t.configure(yscrollcommand=scroll.set)
        t.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y');return t

    def inputs(self,parent,names):
        frame=ttk.LabelFrame(parent,text='Saisie',padding=9);frame.pack(fill='x',pady=9)
        entries={}
        for i,name in enumerate(names):
            ttk.Label(frame,text=name).grid(row=i//3*2,column=i%3,sticky='w',padx=5)
            ent=ttk.Entry(frame,width=32);ent.grid(row=i//3*2+1,column=i%3,sticky='ew',padx=5,pady=3)
            entries[name]=ent
        for i in range(3):frame.columnconfigure(i,weight=1)
        return frame,entries

    def decision_form(self):
        f,self.d=self.inputs(self.dec,['ID décision','Titre','Justification','Auteur','Approbateur'])
        ttk.Button(f,text='Proposer',command=lambda:self.run(lambda:self.g.propose(*[self.d[n].get().strip() for n in ['ID décision','Titre','Justification','Auteur']]))).grid(row=4,column=0,pady=8)
        for i,(label,status) in enumerate([('Approuver','APPROVED'),('Refuser','REJECTED'),('Reporter','DEFERRED')],1):
            ttk.Button(f,text=label,command=lambda s=status:self.run(lambda:self.g.decide(self.d['ID décision'].get().strip(),self.d['Approbateur'].get().strip(),s))).grid(row=4,column=i%3,pady=8,sticky='e' if i==3 else 'w')

    def reservation_form(self):
        f,self.r=self.inputs(self.res,['ID réserve','ID décision','Description','Responsable','Preuve','Acteur clôture'])
        self.blocking=tk.BooleanVar(value=True)
        ttk.Checkbutton(f,text='Bloquante',variable=self.blocking).grid(row=4,column=0,sticky='w')
        ttk.Button(f,text='Ajouter réserve',command=lambda:self.run(lambda:self.g.add_reservation(*[self.r[n].get().strip() for n in ['ID réserve','ID décision','Description','Responsable']],blocking=self.blocking.get()))).grid(row=4,column=1)
        ttk.Button(f,text='Résoudre avec preuve',command=lambda:self.run(lambda:self.g.resolve_reservation(self.r['ID réserve'].get().strip(),self.r['Acteur clôture'].get().strip(),self.r['Preuve'].get().strip()))).grid(row=4,column=2)

    def artifact_form(self):
        self.artifact_table=self.table(self.art,('ID','Type','Titre','État','Responsable','Référence'))
        f,self.a=self.inputs(self.art,['ID objet','Titre','Responsable','Référence','ID décision','Acteur'])
        self.kind=tk.StringVar(value='ACTION')
        ttk.Combobox(f,textvariable=self.kind,values=sorted(Traceability.TYPES),state='readonly',width=15).grid(row=4,column=0,sticky='w')
        ttk.Button(f,text='Créer',command=lambda:self.run(lambda:self.trace.add(self.a['ID objet'].get().strip(),self.kind.get(),self.a['Titre'].get().strip(),self.a['Responsable'].get().strip(),self.a['Référence'].get().strip(),self.a['Acteur'].get().strip() or None))).grid(row=4,column=1)
        ttk.Button(f,text='Lier à décision',command=lambda:self.run(lambda:self.trace.link(self.a['ID décision'].get().strip(),self.a['ID objet'].get().strip(),self.a['Acteur'].get().strip()))).grid(row=4,column=2)
        ttk.Button(f,text='Terminer avec preuve',command=lambda:self.run(lambda:self.trace.complete(self.a['ID objet'].get().strip(),self.a['Acteur'].get().strip(),self.a['Référence'].get().strip()))).grid(row=5,column=0,pady=5)
        ttk.Button(f,text='Contrôler clôture',command=self.check_closure).grid(row=5,column=1,pady=5)
        ttk.Button(f,text='Exporter diagnostic JSON',command=self.export_closure).grid(row=5,column=2,pady=5)

    def meeting_form(self):
        self.meeting_table=self.table(self.meet,('ID','Objet','Date','Président','État'))
        f,self.m=self.inputs(self.meet,['ID comité','Objet','Date ISO','Président','Participant','Rôle','ID décision','Acteur','Compte rendu'])
        actions=[('Créer',lambda:self.committees.create(*[self.m[n].get().strip() for n in ['ID comité','Objet','Date ISO','Président']])),
                 ('Participant',lambda:self.committees.attendee(*[self.m[n].get().strip() for n in ['ID comité','Participant','Rôle','Acteur']])),
                 ('Lier décision',lambda:self.committees.link(*[self.m[n].get().strip() for n in ['ID comité','ID décision','Acteur']])),
                 ('Tenir séance',lambda:self.committees.hold(*[self.m[n].get().strip() for n in ['ID comité','Acteur','Compte rendu']])),
                 ('Clôturer',lambda:self.committees.close(self.m['ID comité'].get().strip(),self.m['Acteur'].get().strip(),self.trace))]
        for i,(label,action) in enumerate(actions):
            ttk.Button(f,text=label,command=lambda fn=action:self.run(fn)).grid(row=6+i//3,column=i%3,padx=3,pady=4)
        ttk.Button(f,text='Exporter CR Markdown',command=self.export_meeting).grid(row=8,column=0,pady=4)

    def planning_form(self):
        frame,self.p=self.inputs(self.meet,['ID suivi','ID comité suivi','ID décision suivie','Responsable suivi','Échéance YYYY-MM-DD','Objet suivi','Acteur suivi','Preuve suivi'])
        ttk.Button(frame,text='Ajouter suivi',command=lambda:self.run(lambda:self.planning.add_followup(*[self.p[n].get().strip() for n in ['ID suivi','ID comité suivi','ID décision suivie','Responsable suivi','Échéance YYYY-MM-DD','Objet suivi','Acteur suivi']]))).grid(row=6,column=0,pady=4)
        ttk.Button(frame,text='Clôturer suivi',command=lambda:self.run(lambda:self.planning.complete(self.p['ID suivi'].get().strip(),self.p['Acteur suivi'].get().strip(),self.p['Preuve suivi'].get().strip()))).grid(row=6,column=1,pady=4)
        ttk.Button(frame,text='Exporter ordre du jour',command=self.export_agenda).grid(row=6,column=2,pady=4)
        ttk.Button(frame,text='Calendrier et relances',command=self.export_calendar).grid(row=7,column=0,pady=4)

    def month_form(self):
        from datetime import date
        now=date.today()
        bar=ttk.Frame(self.month_tab);bar.pack(fill='x',pady=5)
        self.month_year=tk.IntVar(value=now.year)
        self.month_number=tk.IntVar(value=now.month)
        self.month_owner=tk.StringVar()
        self.month_status=tk.StringVar()
        for label,var,width in [('Année',self.month_year,7),('Mois',self.month_number,4),('Responsable',self.month_owner,20)]:
            ttk.Label(bar,text=label).pack(side='left',padx=3)
            ttk.Entry(bar,textvariable=var,width=width).pack(side='left',padx=3)
        ttk.Label(bar,text='État comité').pack(side='left',padx=3)
        ttk.Combobox(bar,textvariable=self.month_status,values=['','DRAFT','HELD','CLOSED'],state='readonly',width=10).pack(side='left',padx=3)
        ttk.Button(bar,text='Afficher',command=self.render_month).pack(side='left',padx=8)
        self.month_grid=ttk.Frame(self.month_tab);self.month_grid.pack(fill='both',expand=True)
        self.month_details=tk.Text(self.month_tab,height=7,wrap='word',state='disabled')
        self.month_details.pack(fill='x',pady=5)
        self.render_month()

    def render_month(self):
        try:
            data=self.month_view.build(self.month_year.get(),self.month_number.get(),self.month_owner.get().strip(),self.month_status.get())
            for widget in self.month_grid.winfo_children():widget.destroy()
            for col,name in enumerate(['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']):
                ttk.Label(self.month_grid,text=name,anchor='center',font=('Segoe UI',10,'bold')).grid(row=0,column=col,sticky='ew')
                self.month_grid.columnconfigure(col,weight=1)
            for row,week in enumerate(data['weeks'],1):
                self.month_grid.rowconfigure(row,weight=1)
                for col,day in enumerate(week):
                    events=data['days'].get(day.isoformat(),[])
                    caption=f'{day.day}  • {len(events)} événement(s)' if events else str(day.day)
                    btn=ttk.Button(self.month_grid,text=caption,command=lambda d=day,e=events:self.show_month_day(d,e))
                    btn.grid(row=row,column=col,sticky='nsew',padx=2,pady=2)
                    if day.month!=data['month']:btn.state(['disabled'])
            self.show_month_day(date(data['year'],data['month'],1),data['days'].get(date(data['year'],data['month'],1).isoformat(),[]))
        except (ValueError,OverflowError) as exc:
            messagebox.showerror('Calendrier',str(exc))

    def show_month_day(self,day,events):
        lines=[day.isoformat(),'']
        for e in events:
            if e['kind']=='MEETING':lines.append(f"COMITÉ {e['id']} — {e['title']} ({e['status']})")
            else:lines.append(f"ACTION {e['id']} — {e['owner']} / {e['description']} (décision {e['decision_id']})")
        if not events:lines.append('Aucun événement')
        self.month_details.configure(state='normal')
        self.month_details.delete('1.0','end')
        self.month_details.insert('1.0','\n'.join(lines))
        self.month_details.configure(state='disabled')

    def export_calendar(self):
        try:
            content,digest=self.calendar.report()
            path=filedialog.asksaveasfilename(defaultextension='.md',filetypes=[('Markdown','*.md')])
            if path:
                Path(path).write_text(content,encoding='utf-8')
                Path(path+'.sha256').write_text(digest+'  '+Path(path).name+'\n',encoding='utf-8')
                messagebox.showinfo('Export','Calendrier et brouillons de relance exportés (aucun envoi)')
        except Exception as exc: messagebox.showerror('Export refusé',str(exc))

    def export_agenda(self):
        try:
            content,digest=self.planning.agenda_markdown(self.p['ID comité suivi'].get().strip())
            path=filedialog.asksaveasfilename(defaultextension='.md',filetypes=[('Markdown','*.md')])
            if path:
                Path(path).write_text(content,encoding='utf-8')
                Path(path+'.sha256').write_text(digest+'  '+Path(path).name+'\n',encoding='utf-8')
                messagebox.showinfo('Export','Ordre du jour exporté')
        except Exception as exc: messagebox.showerror('Export refusé',str(exc))

    def export_meeting(self):
        try:
            content,digest=self.committees.report(self.m['ID comité'].get().strip())
            path=filedialog.asksaveasfilename(defaultextension='.md',filetypes=[('Markdown','*.md')])
            if path:
                Path(path).write_text(content,encoding='utf-8')
                Path(path+'.sha256').write_text(digest+'  '+Path(path).name+'\n',encoding='utf-8')
                messagebox.showinfo('Export', 'Compte rendu et SHA-256 exportés')
        except Exception as exc: messagebox.showerror('Erreur',str(exc))

    def dashboard_form(self):
        bar=ttk.Frame(self.dashboard);bar.pack(fill='x')
        self.kpis=ttk.Label(bar,text='',font=('Segoe UI',11,'bold'))
        self.kpis.pack(side='left',fill='x',expand=True)
        ttk.Button(bar,text='Actualiser',command=self.refresh).pack(side='right')
        chooser=ttk.Frame(self.dashboard);chooser.pack(fill='x',pady=8)
        ttk.Label(chooser,text='Décision :').pack(side='left')
        self.selected_decision=tk.StringVar()
        self.decision_picker=ttk.Combobox(chooser,textvariable=self.selected_decision,state='readonly',width=34)
        self.decision_picker.pack(side='left',padx=8)
        self.decision_picker.bind('<<ComboboxSelected>>',lambda event:self.draw_graph())
        ttk.Label(chooser,text='Rechercher dans toutes les décisions :').pack(side='left',padx=(12,3))
        self.graph_query=tk.StringVar()
        graph_search=ttk.Entry(chooser,textvariable=self.graph_query,width=24)
        graph_search.pack(side='left',padx=3)
        graph_search.bind('<Return>',lambda event:self.search_graph_decisions())
        ttk.Button(chooser,text='Rechercher',command=self.search_graph_decisions).pack(side='left',padx=3)
        self.graph_matches=self.table(self.dashboard,('ID','Titre','État','Auteur'))
        self.graph_matches.configure(height=3)
        self.graph_matches.bind('<Double-1>',self.open_graph_match)
        self.graph_matches.bind('<Return>',self.open_graph_match)

        graph_controls=ttk.Frame(self.dashboard);graph_controls.pack(fill='x',pady=3)
        ttk.Label(graph_controls,text='Filtrer le graphe :').pack(side='left')
        self.graph_filter=tk.StringVar()
        graph_filter_entry=ttk.Entry(graph_controls,textvariable=self.graph_filter,width=24)
        graph_filter_entry.pack(side='left',padx=4)
        graph_filter_entry.bind('<Return>',lambda event:self.draw_graph())
        ttk.Button(graph_controls,text='Appliquer',command=self.draw_graph).pack(side='left')
        self.graph_kind=tk.StringVar(value='TOUS')
        ttk.Combobox(graph_controls,textvariable=self.graph_kind,state='readonly',width=13,
                     values=('TOUS','RÉSERVE','ADR','ACTION','EVIDENCE','DOCUMENT')).pack(side='left',padx=6)
        ttk.Button(graph_controls,text='Filtrer type',command=self.draw_graph).pack(side='left')
        self.graph_collapsed=set()
        self.graph_page_limit=60
        self.graph_group=tk.StringVar(value='TOUS')
        ttk.Combobox(graph_controls,textvariable=self.graph_group,state='readonly',width=13,
                     values=('TOUS','RÉSERVE','ADR','ACTION','PREUVE','DOCUMENT')).pack(side='left',padx=3)
        ttk.Button(graph_controls,text='Masquer/afficher groupe',command=self.toggle_graph_group).pack(side='left',padx=3)
        ttk.Button(graph_controls,text='Voir plus (+60)',command=self.expand_graph).pack(side='left',padx=3)
        ttk.Button(graph_controls,text='Réduire',command=self.reset_graph_limit).pack(side='left',padx=3)
        ttk.Button(graph_controls,text='SVG',command=lambda:self.export_graph('svg')).pack(side='left',padx=2)
        ttk.Button(graph_controls,text='PNG',command=lambda:self.export_graph('png')).pack(side='left',padx=2)
        self.graph_zoom=1.0
        ttk.Button(graph_controls,text='−',width=3,command=lambda:self.zoom_graph(0.8)).pack(side='right')
        ttk.Button(graph_controls,text='+',width=3,command=lambda:self.zoom_graph(1.25)).pack(side='right')
        ttk.Button(graph_controls,text='100 %',command=self.reset_graph_zoom).pack(side='right',padx=4)
        graph_area=ttk.Frame(self.dashboard);graph_area.pack(fill='both',expand=True)
        self.graph=tk.Canvas(graph_area,bg='#ffffff',height=300,highlightthickness=1,highlightbackground='#cbd5e1')
        self.graph.pack(side='left',fill='both',expand=True)
        self.graph_minimap=tk.Canvas(self.graph,width=180,height=115,bg='#f8fafc',highlightthickness=1,highlightbackground='#94a3b8',cursor='crosshair')
        self.graph_minimap.place(relx=1.0,rely=1.0,anchor='se',x=-14,y=-14)
        self.graph_minimap.bind('<Button-1>',self.minimap_navigate)
        scrollbar=ttk.Scrollbar(graph_area,orient='vertical',command=self._graph_yview)
        scrollbar.pack(side='right',fill='y')
        hscroll=ttk.Scrollbar(self.dashboard,orient='horizontal',command=self._graph_xview)
        hscroll.pack(fill='x')
        self.graph.configure(yscrollcommand=lambda a,b:(scrollbar.set(a,b),self.after_idle(self.update_minimap)),
                             xscrollcommand=lambda a,b:(hscroll.set(a,b),self.after_idle(self.update_minimap)))
        self._graph_after=None
        self._prepare_queue=queue.Queue()
        self._prepare_scheduler=RouteScheduler(lambda positions, center, cancel_check=None: prepare_graph(positions[0],cancel_check=cancel_check),self._prepare_queue.put)
        self._prepare_generation=0
        self._prepare_pending=None
        self._prepare_cache={}
        self._prepare_poll_id=None
        self._prepare_ms=None
        self._route_generation=0
        self._route_cache={}
        self._route_pending=None
        self._route_queue=queue.Queue()
        self._route_scheduler=RouteScheduler(scalable_obstacle_routes,self._route_queue.put)
        self._route_poll_id=None
        self._diag_queue=queue.Queue()
        self._diag_scheduler=RouteScheduler(diagnose_routes,self._diag_queue.put)
        self._diag_generation=0
        self._diag_key=None
        self._diag_result=None
        self._diag_poll_id=None
        self._render_started=None
        self._render_ms=None
        self._viewport_job=None
        self._viewport_model=None
        self.graph.bind('<Configure>',self.schedule_graph)
        self.graph.bind('<ButtonPress-1>',lambda e:self.graph.scan_mark(e.x,e.y))
        self.graph.bind('<B1-Motion>',lambda e:self.graph.scan_dragto(e.x,e.y,gain=1))
        self.graph.bind('<MouseWheel>',self.graph_mousewheel)
        self.graph.bind('<ButtonRelease-1>',lambda e:self._schedule_viewport_render())
        self.graph.bind('<Button-4>',lambda e:(self.graph.yview_scroll(-3,'units'),self._schedule_viewport_render()))
        self.graph.bind('<Button-5>',lambda e:(self.graph.yview_scroll(3,'units'),self._schedule_viewport_render()))
        self.graph.bind('<Shift-MouseWheel>',lambda e:(self.graph.xview_scroll(-3 if e.delta>0 else 3,'units'),self.after_idle(self.update_minimap)))
        self.graph_note=ttk.Label(self.dashboard,text='Vue des dépendances : décision → réserves / ADR / actions / preuves / documents',foreground='#475569')
        self.graph_note.pack(anchor='w',pady=5)

    def search_graph_decisions(self):
        try:
            results=find_decisions(self.g.db,self.graph_query.get())
            self.graph_matches.delete(*self.graph_matches.get_children())
            for row in results:
                self.graph_matches.insert('', 'end',iid=row['id'],values=(row['id'],row['title'],row['status'],row['author']))
            self.graph_note.configure(text=f'{len(results)} résultat(s) affiché(s) (maximum 30). Double-cliquer pour ouvrir le graphe.')
        except Exception as exc:
            self.graph_note.configure(text=f'Recherche indisponible : {exc}')

    def select_graph_decision(self, decision_id):
        """Navigate to any decision, including those outside the 500-item picker."""
        if not self.g.db.execute('SELECT 1 FROM decisions WHERE id=?',(decision_id,)).fetchone():
            return False
        values=list(self.decision_picker.cget('values'))
        if decision_id not in values:
            values=[decision_id]+values[:499]
            self.decision_picker.configure(values=values)
        self.selected_decision.set(decision_id)
        self.draw_graph()
        return True

    def open_graph_match(self, event=None):
        selected=self.graph_matches.selection()
        if selected:self.select_graph_decision(selected[0])

    def schedule_graph(self, event=None):
        if self._graph_after is not None:
            self.after_cancel(self._graph_after)
        self._graph_after=self.after(120,self.draw_graph)

    def zoom_graph(self, factor):
        self.graph_zoom=max(0.5,min(2.5,round(self.graph_zoom*factor,3)))
        self.draw_graph()

    def reset_graph_zoom(self):
        self.graph_zoom=1.0
        self.draw_graph()

    def export_graph(self, extension):
        did=self.selected_decision.get()
        if not did:
            messagebox.showwarning('Export graphe','Sélectionnez une décision.');return
        path=filedialog.asksaveasfilename(defaultextension='.'+extension,
            filetypes=[(extension.upper(), '*.'+extension)])
        if not path:return
        try:
            model=self._graph_export_model()
            if extension=='svg':export_svg(model,path)
            else:export_png(model,path)
            messagebox.showinfo('Export graphe',f'Graphe exporté : {path}')
        except Exception as exc:messagebox.showerror('Export impossible',str(exc))

    def _graph_export_model(self):
        model=decision_graph(self.g.db,self.selected_decision.get())
        nodes=[('RÉSERVE',r['id'],r['status'],bool(r['blocking']) and r['status']=='OPEN') for r in model['reservations']]
        nodes += [(a['kind'],a['id'],a['state'],a['kind']=='ACTION' and a['state']=='OPEN') for a in model['artifacts']]
        kind=self.graph_kind.get()
        nodes=filter_nodes(nodes,None if kind=='TOUS' else (kind,),self.graph_filter.get())
        nodes,_,_=grouped_nodes(nodes,self.graph_collapsed,self.graph_page_limit)
        return {'title':self.selected_decision.get(),'nodes':nodes}

    def graph_mousewheel(self,event):
        if event.state & 0x0004:  # Ctrl + wheel: zoom
            self.zoom_graph(1.25 if event.delta>0 else 0.8)
        else:
            self.graph.yview_scroll(-3 if event.delta>0 else 3,'units')
            self._schedule_viewport_render()

    def toggle_graph_group(self):
        kind=self.graph_group.get()
        if kind=='TOUS':
            self.graph_collapsed=set() if self.graph_collapsed else {'RÉSERVE','ADR','ACTION','PREUVE','DOCUMENT'}
        elif kind in self.graph_collapsed:self.graph_collapsed.remove(kind)
        else:self.graph_collapsed.add(kind)
        self.draw_graph()

    def expand_graph(self):
        self.graph_page_limit=min(10000,self.graph_page_limit+60)
        self.draw_graph()

    def reset_graph_limit(self):
        self.graph_page_limit=60
        self.draw_graph()

    def _request_routes(self, key, positions, center):
        """Compute immutable geometry off the Tk thread; never touch Tk in worker."""
        self._route_generation += 1
        generation = self._route_generation
        self._route_pending = key
        self._route_scheduler.submit(generation, key, positions, center)
        if self._route_poll_id is None:
            self._route_poll_id = self.after(40, self._poll_routes)

    def _poll_routes(self):
        self._route_poll_id = None
        latest = None
        while True:
            try:
                candidate = self._route_queue.get_nowait()
                if candidate[0] == self._route_generation:
                    latest = candidate
            except queue.Empty: break
        if latest is not None:
            generation, key, routes, error = latest
            if generation == self._route_generation and key == self._route_pending:
                self._route_pending = None
                if routes is not None:
                    self._route_cache[key] = routes
                    self._diag_generation+=1
                    self._diag_key=key
                    self._diag_result=None
                    self._diag_scheduler.submit(self._diag_generation,key,routes,0)
                    if self._diag_poll_id is None:self._diag_poll_id=self.after(80,self._poll_diagnostics)
                    if len(self._route_cache)>12:
                        self._route_cache.pop(next(iter(self._route_cache)))
                    self.draw_graph()
                else:
                    self.graph_note.configure(text=f'Routage indisponible : {error}')
        if self._route_pending is not None:
            self._route_poll_id = self.after(40, self._poll_routes)

    def _poll_diagnostics(self):
        self._diag_poll_id=None
        newest=None
        while True:
            try:
                candidate=self._diag_queue.get_nowait()
                if candidate[0]==self._diag_generation and candidate[1]==self._diag_key:newest=candidate
            except queue.Empty:break
        if newest is not None:
            _,key,value,error=newest
            self._diag_result=value if error is None else {'error':error}
            self._update_graph_note()
        elif self._diag_key is not None and self._diag_result is None:
            self._diag_poll_id=self.after(80,self._poll_diagnostics)

    def _update_graph_note(self):
        if not hasattr(self,'_graph_status'):return
        suffix=''
        if self._render_ms is not None:suffix+=f' · rendu visible {self._render_ms:.1f} ms'
        diag=self._diag_result
        if diag and 'interference' in diag:
            suffix+=f" · diagnostic {diag['sampled']}/{diag['total']} tracés"
            if not diag['complete']:suffix+=' (échantillon)'
        self.graph_note.configure(text=self._graph_status+suffix)

    def _cancel_card_render(self):
        """Invalidate scheduled Tk batches before clearing or closing canvas."""
        self._card_render_generation = getattr(self, '_card_render_generation', 0) + 1
        job = getattr(self, '_card_render_job', None)
        if job is not None:
            try: self.after_cancel(job)
            except tk.TclError: pass
        self._card_render_job = None

    def _viewport_bounds(self):
        c=self.graph
        left=c.canvasx(0); top=c.canvasy(0)
        return (left,top,left+max(1,c.winfo_width()),top+max(1,c.winfo_height()))

    def _schedule_viewport_render(self):
        if getattr(self,'_viewport_job',None) is not None:
            try:self.after_cancel(self._viewport_job)
            except tk.TclError:pass
        self._viewport_job=self.after(35,self._render_viewport)

    def _render_viewport(self):
        self._viewport_job=None
        model=getattr(self,'_viewport_model',None)
        if model is None:return
        positions,routes,zoom,cards_idx,routes_idx=model
        bounds=self._viewport_bounds()
        c=self.graph
        self._cancel_card_render()
        self._render_started=time.perf_counter()
        c.delete('graph-card');c.delete('graph-route')
        for route in routes_idx.query(bounds,zoom):
            item=c.create_line(*[coord for point in route for coord in point],fill='#94a3b8',width=2,tags=('graph-route',))
            c.scale(item,0,0,zoom,zoom)
            c.tag_lower(item)
        cards=cards_idx.query(bounds,zoom)
        self._render_card_batch(self._card_render_generation,cards,zoom)
        self.after_idle(self.update_minimap)

    def _render_card_batch(self, generation, positions, zoom, offset=0):
        """Create only viewport cards in bounded batches."""
        if generation != self._card_render_generation:return
        c=self.graph
        for node,x,y in positions[offset:offset+40]:
            kind,identifier,state,critical=node
            fill='#fee2e2' if critical else '#dcfce7' if state in ('DONE','RESOLVED') else '#f1f5f9'
            outline='#dc2626' if critical else '#94a3b8'
            rect=c.create_rectangle(x-95,y-24,x+95,y+24,fill=fill,outline=outline,tags=('graph-card',))
            label=c.create_text(x,y-8,text=f'{kind} · {identifier[:22]}',font=('Segoe UI',9,'bold'),width=180,tags=('graph-card',))
            state_label=c.create_text(x,y+10,text=state,fill='#475569',tags=('graph-card',))
            for item in (rect,label,state_label):c.scale(item,0,0,zoom,zoom)
        end=offset+40
        if end<len(positions):
            self._card_render_job=self.after(1,lambda:self._render_card_batch(generation,positions,zoom,end))
        else:
            self._card_render_job=None
            if self.__dict__.get('_render_started') is not None:
                self._render_ms=(time.perf_counter()-self._render_started)*1000
                self._update_graph_note()
            self.after_idle(self.update_minimap)

    def _prepare_request(self):
        viewport=max(self.graph.winfo_width(),550)
        return (str(self.dbpath),self.selected_decision.get(),self.graph_kind.get(),
                self.graph_filter.get(),tuple(sorted(self.graph_collapsed)),self.graph_page_limit,viewport,database_fingerprint(self.dbpath))

    def _poll_preparation(self):
        self._prepare_poll_id=None
        latest=None
        while True:
            try:
                item=self._prepare_queue.get_nowait()
                if item[0]==self._prepare_generation:latest=item
            except queue.Empty:break
        if latest is not None:
            generation,request,result,error=latest
            if request==self._prepare_pending:
                self._prepare_pending=None
                if error:
                    self.graph_note.configure(text='Préparation indisponible : '+error)
                else:
                    self._prepare_ms=(time.perf_counter()-self._prepare_started)*1000
                    self._prepare_cache[request]=result
                    if len(self._prepare_cache)>6:self._prepare_cache.pop(next(iter(self._prepare_cache)))
                    self.draw_graph()
        if self._prepare_pending is not None:
            self._prepare_poll_id=self.after(40,self._poll_preparation)

    def draw_graph(self):
        self._graph_after=None
        c=self.graph
        did=self.selected_decision.get()
        if not did:
            self._cancel_card_render();self._viewport_model=None;c.delete('all')
            c.create_text(25,40,text='Sélectionner une décision',anchor='w');return
        request=self._prepare_request()
        prepared=self._prepare_cache.get(request)
        if prepared is not None and self._prepare_pending is not None and self._prepare_pending != request:
            self._prepare_generation+=1
            self._prepare_pending=None
        if prepared is None:
            if request!=self._prepare_pending:
                self._prepare_generation+=1
                self._prepare_pending=request
                self._prepare_started=time.perf_counter()
                self._prepare_scheduler.submit(self._prepare_generation,request,request,0)
                if self._prepare_poll_id is None:self._prepare_poll_id=self.after(40,self._poll_preparation)
            self.graph_note.configure(text='Préparation du graphe en arrière-plan…')
            return
        self._cancel_card_render()
        self._viewport_model=None
        c.delete('all')
        status,positions,width,height,group_count,remaining=prepared
        viewport=request[-2]
        center=width/2
        c.create_rectangle(center-130,16,center+130,68,fill='#dbeafe',outline='#2563eb',width=2,tags='diagram')
        c.create_text(center,42,text=f'{did} · {status}',width=245,font=('Segoe UI',10,'bold'),tags='diagram')
        if not positions:c.create_text(center,130,text='Aucune dépendance correspondant aux filtres',fill='#64748b',tags='diagram')
        zoom=self.graph_zoom
        center=width/2
        c.create_rectangle(center-130,16,center+130,68,fill='#dbeafe',outline='#2563eb',width=2,tags='diagram')
        c.create_text(center,42,text=f"{did} · {model['decision']['status']}",width=245,font=('Segoe UI',10,'bold'),tags='diagram')
        if not nodes:
            c.create_text(center,130,text='Aucune dépendance correspondant aux filtres',fill='#64748b',tags='diagram')
        key=(tuple((tuple(node),round(x,3),round(y,3)) for node,x,y in positions),round(center,3))
        routes=self._route_cache.get(key)
        if routes is not None and self._route_pending is not None and self._route_pending != key:
            self._route_generation += 1
            self._route_pending = None
        if routes is None:
            if self._route_pending != key:
                self._request_routes(key, list(positions), center)
            routes=[]
        obstacles=[(x-95,y-24,x+95,y+24) for _,x,y in positions]
        # Diagnostics exclude each route's destination card (intentional boundary contact).
        intersections=[]  # Full quadratic diagnostic deferred; avoid blocking Tk on large graphs.
        # Connectors are virtualized together with cards in _render_viewport.
        # Root and connectors are scaled immediately; cards arrive in bounded batches.
        c.scale('diagram',0,0,zoom,zoom)
        generation=self._card_render_generation
        self._viewport_model=(positions,routes,zoom,card_index(positions),route_index(routes))
        c.configure(scrollregion=(0,0,max(viewport,width*zoom),max(300,height*zoom)))
        self._graph_content_size=(max(viewport,width*zoom),max(300,height*zoom))
        self._schedule_viewport_render()
        self._graph_status=f'{len(positions)} carte(s) · {group_count} groupe(s) · {remaining} restant(s) · zoom {zoom:.0%} · préparation {self._prepare_ms:.1f} ms · routage {"calcul en cours" if self._route_pending == key else "prêt"}'
        self._update_graph_note()

    def _graph_xview(self,*args):
        self.graph.xview(*args)
        self._schedule_viewport_render()

    def _graph_yview(self,*args):
        self.graph.yview(*args)
        self._schedule_viewport_render()

    def update_minimap(self):
        """Compact overview; does not perform database reads."""
        if not hasattr(self,'graph_minimap'):return
        m=self.graph_minimap;m.delete('all')
        cw,ch=getattr(self,'_graph_content_size',(550,300))
        vw=max(1,self.graph.winfo_width());vh=max(1,self.graph.winfo_height())
        try:
            w,h,box=minimap_viewport(cw,ch,vw,vh,self.graph.canvasx(0),self.graph.canvasy(0))
        except ValueError:return
        m.create_rectangle(0,0,w,h,fill='#e2e8f0',outline='#64748b')
        model=getattr(self,'_viewport_model',None)
        if model is not None:
            positions,_,zoom=model
            for _,x,y in positions:
                m.create_rectangle((x-95)*zoom*w/cw,(y-24)*zoom*h/ch,(x+95)*zoom*w/cw,(y+24)*zoom*h/ch,fill='#94a3b8',outline='')
        m.create_rectangle(*box,outline='#2563eb',width=2)

    def minimap_navigate(self,event):
        cw,ch=getattr(self,'_graph_content_size',(550,300))
        w,h,_=minimap_geometry(cw,ch,max(1,self.graph.winfo_width()),max(1,self.graph.winfo_height()))
        if cw>self.graph.winfo_width():
            self.graph.xview_moveto(minimap_scroll_fraction(event.x,w,cw,self.graph.winfo_width()))
        if ch>self.graph.winfo_height():
            self.graph.yview_moveto(minimap_scroll_fraction(event.y,h,ch,self.graph.winfo_height()))
        self._schedule_viewport_render()

    def check_closure(self):
        try:
            result=self.trace.closure_readiness(self.a['ID décision'].get().strip())
            messagebox.showinfo('Préparation clôture', 'PRÊT POUR REVUE HUMAINE' if result['ready'] else 'BLOQUÉ :\n'+'\n'.join(result['issues']))
        except Exception as exc: messagebox.showerror('Contrôle impossible',str(exc))

    def export_closure(self):
        try:
            data=self.trace.export_json(self.a['ID décision'].get().strip())
            target=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')])
            if target:
                from pathlib import Path
                import os, tempfile
                path=Path(target)
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
                    temp=f.name; f.write(data)
                os.replace(temp,path)
                messagebox.showinfo('Export','Diagnostic enregistré')
        except Exception as exc: messagebox.showerror('Export refusé',str(exc))

    def run(self,fn):
        try:fn();self.refresh()
        except Exception as exc:messagebox.showerror('Action refusée',str(exc))

    def refresh(self):
        if hasattr(self,'_prepare_cache'):self._prepare_cache.clear()
        """Bound visible tables and use SQL aggregates; audit checked once per refresh."""
        db=self.g.db
        for widget,table in ((self.artifact_table,'artifacts'),(self.meeting_table,'meetings'),(self.decision_table,'decisions'),(self.reservation_table,'reservations')):
            widget.delete(*widget.get_children())
            for row in bounded_rows(db,table):
                if table=='reservations':row=(row[0],row[1],row[2],'Oui' if row[3] else 'Non',row[4],row[5])
                widget.insert('', 'end',values=row)
        m=summary_metrics(db)
        self.kpis.configure(text=f"Décisions {m['decisions']}  ·  À valider {m['pending']}  ·  Approuvées {m['approved']}  ·  Réserves bloquantes {m['blocking']}  ·  Actions ouvertes {m['unfinished_actions']}  ·  Preuves manquantes {m['missing_evidence']}")
        # A bounded picker prevents constructing thousands of Tk combobox values.
        ids=[r[0] for r in db.execute('SELECT id FROM decisions ORDER BY id LIMIT 500')]
        self.decision_picker.configure(values=ids)
        if self.selected_decision.get() not in ids:
            current=self.selected_decision.get()
            if current and db.execute('SELECT 1 FROM decisions WHERE id=?',(current,)).fetchone():
                ids=[current]+ids[:499]
                self.decision_picker.configure(values=ids)
            else:self.selected_decision.set(ids[0] if ids else '')
        self.draw_graph()
        self.refresh_portfolio()
        valid=self.g.verify_audit()
        self.summary.configure(text=f"Décisions en attente : {m['pending']}   |   Réserves bloquantes : {m['blocking']}   |   Audit : {'OK' if valid else 'INVALIDE'}   |   Listes limitées à 250 lignes")

    def audit(self):
        messagebox.showinfo('Audit', 'Chaîne SHA-256 valide' if self.g.verify_audit() else 'ATTENTION : chaîne invalide')

    def export(self):
        target=filedialog.asksaveasfilename(defaultextension='.md',filetypes=[('Markdown','*.md')])
        if target:
            try:
                export_snapshot(self.g,target)
                messagebox.showinfo('Export',f'Rapport, synthèse JSON et empreinte SHA-256 enregistrés.\n{target}')
            except Exception as exc:
                messagebox.showerror('Export refusé',str(exc))

    def shutdown(self):
        self._portfolio_generation+=1
        self._route_generation+=1
        self._route_pending=None
        self._cancel_card_render()
        if getattr(self,'_viewport_job',None) is not None:self.after_cancel(self._viewport_job)
        self._prepare_generation+=1
        self._prepare_pending=None
        self._prepare_scheduler.close()
        if self._prepare_poll_id is not None:self.after_cancel(self._prepare_poll_id)
        self._route_scheduler.close()
        self._diag_scheduler.close()
        if self._diag_poll_id is not None:self.after_cancel(self._diag_poll_id)
        if self._route_poll_id is not None:
            self.after_cancel(self._route_poll_id)
            self._route_poll_id=None
        self.g.close()
        self.destroy()

if __name__=='__main__':GovernanceWindow().mainloop()
