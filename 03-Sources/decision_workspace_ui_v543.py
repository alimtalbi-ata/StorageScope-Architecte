"""Integrated read-only governance browser. Author: Abdelhalim Talbi."""

def open_workspace(parent, store, views_path, *, history=None, embedded=False, initial_filters=None, on_filter_ready=None):
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog, filedialog
    from decision_workspace_v542 import workspace
    from decision_visual_v545 import visual_summary, evidence_navigation
    from decision_evidence_v546 import assess_evidence, evidence_overview
    from decision_qualification_v547 import QualificationStore, CRITERIA
    from decision_views_v543 import SavedViews
    from decision_detail_v606 import decision_detail
    window = ttk.Frame(parent) if embedded else tk.Toplevel(parent)
    if not embedded:
        window.title('StorageScope — Gouvernance')
        window.geometry('1200x760')
    saved = SavedViews(views_path)
    controls = ttk.LabelFrame(window, text='Recherche et filtres', padding=10)
    controls.pack(fill='x', padx=10, pady=(8, 2))
    search_row = ttk.Frame(controls)
    search_row.pack(fill='x', pady=(0, 6))
    filter_row = ttk.Frame(controls)
    filter_row.pack(fill='x')
    query = tk.StringVar()
    owner = tk.StringVar()
    status = tk.StringVar(value='all')
    deadline = tk.StringVar(value='all')
    view_name = tk.StringVar()
    if initial_filters is not None:
        if not isinstance(initial_filters, dict) or set(initial_filters) - {'query','owner','status','deadline'}:
            raise ValueError('invalid initial filters')
        from decision_views_v543 import validate_filters
        defaults = {'query':'','owner':None,'status':'all','deadline':'all'}
        defaults.update(initial_filters)
        initial = validate_filters(defaults)
        query.set(initial['query']); owner.set(initial['owner'] or '')
        status.set(initial['status']); deadline.set(initial['deadline'])
    # Grid-based search adapts to available width instead of clipping the second field.
    search_row.columnconfigure(1, weight=3)
    search_row.columnconfigure(3, weight=2)
    for index, (label, variable, width) in enumerate([('Recherche',query,25),('Responsable',owner,18)]):
        ttk.Label(search_row,text=label).grid(row=0,column=index*2,sticky='w',padx=(0,4))
        ttk.Entry(search_row,textvariable=variable,width=width).grid(row=0,column=index*2+1,sticky='ew',padx=(0,10))
    for label, variable, choices in [('Statut',status,('all','OPEN','IN_REVIEW','APPROVED','REJECTED','CLOSED')),
                                     ('Échéance',deadline,('all','overdue','due_today','due_soon','upcoming'))]:
        ttk.Label(filter_row,text=label).pack(side='left')
        ttk.Combobox(filter_row,textvariable=variable,values=choices,width=12,state='readonly').pack(side='left',padx=(4, 12))
    # One-click reset avoids manually clearing four independent filters.
    def reset_filters():
        query.set(''); owner.set(''); status.set('all'); deadline.set('all')
        refresh()
    ttk.Button(filter_row, text='Effacer les filtres', command=reset_filters).pack(side='left', padx=(10, 0))
    # Common tasks are available as one-click presets, without modifying data.
    presets = ttk.Frame(window)
    presets.pack(fill='x', padx=10, pady=(2, 2))
    ttk.Label(presets, text='Accès rapides :').grid(row=0,column=0,sticky='w',padx=(0,6))
    def preset(*, selected_status='all', selected_deadline='all'):
        query.set(''); owner.set(''); status.set(selected_status); deadline.set(selected_deadline)
        refresh()
    ttk.Button(presets, text='Toutes les décisions', command=lambda: preset()).grid(row=0,column=1,sticky='w',padx=3)
    ttk.Button(presets, text='En revue', command=lambda: preset(selected_status='IN_REVIEW')).grid(row=0,column=2,sticky='w',padx=3)
    ttk.Button(presets, text='En retard', command=lambda: preset(selected_deadline='overdue')).grid(row=1,column=1,sticky='w',padx=3,pady=2)
    ttk.Button(presets, text='Aujourd’hui', command=lambda: preset(selected_deadline='due_today')).grid(row=1,column=2,sticky='w',padx=3,pady=2)
    kpis = ttk.Label(window,text='Recherche en attente',padding=8)
    kpis.pack(fill='x')
    # Adjustable master/detail layout: the user can allocate space to the table
    # or the selected decision without hiding the bottom action toolbar.
    split = ttk.Panedwindow(window, orient='vertical')
    split.pack(fill='both', expand=True, padx=10, pady=5)
    tree_scroll = ttk.Frame(split)
    detail_frame = ttk.Frame(split)
    split.add(tree_scroll, weight=4)
    split.add(detail_frame, weight=2)
    tree = ttk.Treeview(tree_scroll, columns=('subject','owner','status','due_date','priority','evidence_reference'), show='tree headings', selectmode='browse')
    tree.heading('#0', text='Décision')
    for col in tree['columns']:
        tree.heading(col, text={'subject':'Sujet', 'owner':'Responsable', 'status':'Statut', 'due_date':'Échéance', 'priority':'Priorité', 'evidence_reference':'Référence de preuve'}.get(col, col))
        tree.column(col, width=140, minwidth=90, stretch=True)
    # Grid guarantees the horizontal scrollbar spans the whole table width.
    tree_scroll.columnconfigure(0, weight=1)
    tree_scroll.rowconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(tree_scroll, orient='vertical', command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    hscroll = ttk.Scrollbar(tree_scroll, orient='horizontal', command=tree.xview)
    hscroll.grid(row=1, column=0, sticky='ew')
    tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=hscroll.set)
    # A browse-only Treeview cannot select all rows: no Ctrl+A binding.
    for priority, color in [('P1','#a62d37'),('P2','#a96912'),('P3','#246e56')]:
        tree.tag_configure(priority, foreground=color)
    ttk.Label(detail_frame, text='Détails de la décision sélectionnée').pack(anchor='w', pady=(2, 4))
    detail = tk.Text(detail_frame, height=7, wrap='word', state='disabled')
    detail.pack(fill='both', expand=True)
    items = {}
    qualification_store = QualificationStore(store.path) if hasattr(store, 'path') else None
    qualification_cache = {}
    def apply_external_filters(values):
        from decision_views_v543 import validate_filters
        current = filters()
        current.update(values)
        validated = validate_filters(current)
        query.set(validated['query']); owner.set(validated['owner'] or '')
        status.set(validated['status']); deadline.set(validated['deadline'])
        refresh()
    if on_filter_ready is not None:
        on_filter_ready(apply_external_filters)
    def filters():
        return {'query':query.get(),'owner':owner.get().strip() or None,'status':status.get(),'deadline':deadline.get()}
    def refresh(*_):
        try:
            selected_before = tree.selection()
            selected_decision = items[selected_before[0]]['id'] if selected_before and selected_before[0] in items else None
            result = workspace(store,**filters())
            tree.delete(*tree.get_children())
            items.clear()
            detail.configure(state='normal')
            detail.delete('1.0','end')
            detail.configure(state='disabled')
            for sheet in result['decision_sheets']:
                node = tree.insert('','end',text=sheet['id'],values=tuple(sheet.get(k,'') for k in tree['columns']))
                items[node] = sheet
            # Restore selection only when the decision is still visible.
            for node, sheet in items.items():
                if sheet['id'] == selected_decision:
                    tree.selection_set(node)
                    tree.see(node)
                    break
            qualification_cache.clear()
            if qualification_store is not None:
                for record in qualification_store.qualifications():
                    qualification_cache[record['decision_id']] = record
            c = visual_summary(result)
            evidence_kpis = evidence_overview(result['decision_sheets'])
            for node, sheet in items.items():
                tree.item(node, tags=(sheet['priority'],))
            stale_count = sum(bool(qualification_cache.get(sheet['id'], {}).get('stale')) for sheet in result['decision_sheets'])
            unreviewed = sum(sheet['id'] not in qualification_cache for sheet in result['decision_sheets'])
            inspect()
            kpis.configure(text=f"À requalifier : {stale_count} | Sans revue : {unreviewed} | Visibles : {c['total']} | P1 : {c['priorities']['P1']} | P2 : {c['priorities']['P2']} | Retards : {c['overdue']} | Revue humaine : {c['human_review']} | Preuves incomplètes : {evidence_kpis['incomplete']} | Audit : {c['audit_head'][:16]}…")
        except (ValueError,KeyError,OSError) as exc:
            tree.delete(*tree.get_children())
            items.clear()
            detail.configure(state='normal')
            detail.delete('1.0','end')
            detail.configure(state='disabled')
            kpis.configure(text='CONSULTATION BLOQUÉE — intégrité ou filtres invalides')
            messagebox.showerror('Gouvernance',str(exc),parent=window)
    def inspect(*_):
        selected = tree.selection()
        if not selected or selected[0] not in items:return
        detail.configure(state='normal')
        detail.delete('1.0','end')
        sheet=items[selected[0]]
        detail.insert('1.0',decision_detail(sheet,evidence_navigation(sheet),assess_evidence(sheet),qualification_cache.get(sheet['id'],{'status':'NON_REVUE'})))
        detail.configure(state='disabled')
    tree.bind('<<TreeviewSelect>>',inspect)
    tree.bind('<Return>',inspect)
    # Filters apply immediately on Enter and are reset without losing the current page.
    for row in (search_row, filter_row):
        for control in row.winfo_children():
            if isinstance(control, (ttk.Entry, ttk.Combobox)):
                control.bind('<Return>', refresh)

    def show_chronology():
        ident=selected_id()
        if not ident:
            messagebox.showinfo('Chronologie','Sélectionnez une décision',parent=window)
            return
        try:
            from decision_timeline_presentation_v553 import STATUS
            from decision_timeline_export_v554 import filtered_timeline, export_timeline
            record=filtered_timeline(store,ident)
            timeline_window=tk.Toplevel(window)
            timeline_window.title('Chronologie des preuves — '+ident)
            timeline_window.geometry('950x550')
            columns=('sequence','label','qualification_verdict','state_label')
            grid=ttk.Treeview(timeline_window,columns=columns,show='headings')
            for column in columns:
                grid.heading(column,text=column.title())
                grid.column(column,width=130 if column!='label' else 240)
            grid.pack(fill='both',expand=True,padx=10,pady=10)
            for state,(_,color) in STATUS.items():
                grid.tag_configure(state,foreground=color)
            ttk.Label(timeline_window,text=f"État : {record['current_label']} | Revues : {record['review_count']}").pack(pady=3)
            event_details=tk.Text(timeline_window,height=12,wrap='word',state='disabled')
            event_details.pack(fill='both',padx=10,pady=8)
            filters_bar=ttk.Frame(timeline_window)
            filters_bar.pack(fill='x',padx=10)
            state_filter=tk.StringVar(value='ALL')
            type_filter=tk.StringVar(value='ALL')
            ttk.Label(filters_bar,text='État').pack(side='left')
            ttk.Combobox(filters_bar,textvariable=state_filter,values=('ALL',*STATUS),state='readonly',width=14).pack(side='left',padx=4)
            ttk.Label(filters_bar,text='Événement').pack(side='left')
            ttk.Combobox(filters_bar,textvariable=type_filter,values=('ALL',*sorted({e['type'] for e in record['events']})),state='readonly',width=24).pack(side='left',padx=4)
            import json
            lookup={}
            def redraw():
                result=filtered_timeline(store,ident,state=state_filter.get(),event_type=type_filter.get())
                grid.delete(*grid.get_children())
                lookup.clear()
                event_details.configure(state='normal')
                event_details.delete('1.0','end')
                event_details.configure(state='disabled')
                for event in result['events']:
                    row=grid.insert('','end',values=tuple(str(event.get(k) if event.get(k) is not None else '') for k in columns),tags=(event['state'],))
                    lookup[row]={'evenement_et_preuves':event,'audit_head':result['audit_head']}
            def export_visible():
                path=filedialog.asksaveasfilename(parent=timeline_window,defaultextension='.json',filetypes=[('JSON','*.json'),('CSV','*.csv')])
                if not path:return
                try:
                    fmt='csv' if path.lower().endswith('.csv') else 'json'
                    export_timeline(store,ident,path,format=fmt,state=state_filter.get(),event_type=type_filter.get())
                except (ValueError,KeyError,OSError) as exc:
                    messagebox.showerror('Export bloqué',str(exc),parent=timeline_window)
            ttk.Button(filters_bar,text='Filtrer',command=redraw).pack(side='left',padx=4)
            ttk.Button(filters_bar,text='Exporter la sélection',command=export_visible).pack(side='left',padx=4)
            def export_committee():
                from decision_committee_evidence_v555 import export_committee_evidence
                path=filedialog.asksaveasfilename(parent=timeline_window,defaultextension='.md',filetypes=[('Markdown','*.md'),('JSON','*.json')])
                if not path:return
                try:
                    export_committee_evidence(store,ident,path,format='json' if path.lower().endswith('.json') else 'md')
                except (ValueError,KeyError,OSError) as exc:
                    messagebox.showerror('Synthèse bloquée',str(exc),parent=timeline_window)
            ttk.Button(filters_bar,text='Synthèse comité',command=export_committee).pack(side='left',padx=4)
            redraw()
            def inspect_event(*_):
                selected=grid.selection()
                if not selected or selected[0] not in lookup:return
                event_details.configure(state='normal')
                event_details.delete('1.0','end')
                event_details.insert('1.0',json.dumps(lookup[selected[0]],ensure_ascii=False,indent=2))
                event_details.configure(state='disabled')
            grid.bind('<<TreeviewSelect>>',inspect_event)
            ttk.Label(timeline_window,text='Lecture seule · qualifications humaines · aucune activation en production').pack(pady=4)
        except (ValueError,KeyError,OSError) as exc:
            messagebox.showerror('Chronologie bloquée',str(exc),parent=window)

    # Separate committee commands from saved-view management: avoids an overflowing toolbar.
    bar=ttk.LabelFrame(window,text='Comité et historique',padding=6)
    bar.pack(fill='x',padx=10,pady=(2, 3))
    views_bar=ttk.LabelFrame(window,text='Vues enregistrées',padding=6)
    views_bar.pack(fill='x',padx=10,pady=(0, 3))
    ttk.Button(filter_row,text='Actualiser',command=refresh).pack(side='left',padx=3)
    ttk.Button(bar,text='Historique',command=show_chronology).pack(side='left',padx=3)
    def export_actions():
        from decision_committee_actions_v556 import export_committee_actions
        path = filedialog.asksaveasfilename(parent=window,defaultextension='.md',filetypes=[('Markdown','*.md'),('JSON','*.json')])
        if not path: return
        try:
            export_committee_actions(store,path,format='json' if path.lower().endswith('.json') else 'md',
                                     owner=owner.get().strip() or None,status=status.get(),
                                     deadline='all' if deadline.get() == 'due_soon' else deadline.get())
            messagebox.showinfo('Comité','Synthèse des actions exportée',parent=window)
        except (ValueError,KeyError,OSError) as exc:
            messagebox.showerror('Comité',str(exc),parent=window)
    ttk.Button(bar,text='Actions comité',command=export_actions).pack(side='left',padx=3)
    def record_committee_resolution():
        from tkinter import simpledialog
        from datetime import date
        from decision_committee_resolution_v558 import CommitteeResolutionStore
        ident=selected_id()
        if not ident:return
        from decision_guided_forms_v607 import guided_committee_form
        values=guided_committee_form(window)
        if values is None:return
        try:
            CommitteeResolutionStore(store.path).resolve(ident,values['actor'],values['meeting_date'],values['verdict'],values['rationale'])
            refresh()
            messagebox.showinfo('Comité','Résolution humaine auditée, sans activation en production',parent=window)
        except (ValueError,KeyError,OSError) as exc:
            messagebox.showerror('Comité',str(exc),parent=window)
    ttk.Button(bar,text='Décision comité',command=record_committee_resolution).pack(side='left',padx=3)

    def open_action_register():
        from decision_committee_register_v557 import action_register, export_action_register
        dialog=tk.Toplevel(window)
        dialog.title('Registre des actions — comité v5.57')
        dialog.geometry('1050x580')
        panel=ttk.Frame(dialog,padding=8);panel.pack(fill='x')
        action_owner=tk.StringVar(value=owner.get().strip())
        action_priority=tk.StringVar(value='ALL')
        action_deadline=tk.StringVar(value='ALL')
        ttk.Label(panel,text='Responsable').pack(side='left')
        ttk.Entry(panel,textvariable=action_owner,width=18).pack(side='left',padx=4)
        for label,var,choices in [('Priorité',action_priority,('ALL','P1','P2','P3')),
                                  ('Échéance',action_deadline,('ALL','overdue','due_soon','upcoming','none'))]:
            ttk.Label(panel,text=label).pack(side='left')
            ttk.Combobox(panel,textvariable=var,values=choices,width=12,state='readonly').pack(side='left',padx=4)
        summary=ttk.Label(dialog,text='');summary.pack(fill='x',padx=10)
        cols=('decision_id','owner','priority','status','due_date','deadline_state','expected_actions')
        register_tree=ttk.Treeview(dialog,columns=cols,show='headings')
        for col in cols:
            register_tree.heading(col,text=col.replace('_',' ').title())
            register_tree.column(col,width=140)
        register_tree.pack(fill='both',expand=True,padx=10,pady=6)
        details=tk.Text(dialog,height=7,state='disabled',wrap='word');details.pack(fill='x',padx=10)
        cache={}
        def params():
            return {'owner':action_owner.get().strip() or None,
                    'priority':action_priority.get(),'deadline':action_deadline.get()}
        def reload():
            try:
                result=action_register(store,**params())
                register_tree.delete(*register_tree.get_children());cache.clear()
                for item in result['actions']:
                    key=register_tree.insert('','end',values=tuple(', '.join(item[col]) if isinstance(item[col],list) else item[col] for col in cols))
                    cache[key]=item
                summary.configure(text=f"Décisions : {result['total']} | Actions humaines : {result['pending']} | Audit : {result['audit_head'][:16]}…")
                details.configure(state='normal');details.delete('1.0','end');details.configure(state='disabled')
            except (ValueError,KeyError,OSError) as exc:
                register_tree.delete(*register_tree.get_children());cache.clear()
                summary.configure(text='CONSULTATION BLOQUÉE')
                messagebox.showerror('Registre',str(exc),parent=dialog)
        def inspect_action(*_):
            selected=register_tree.selection()
            if not selected or selected[0] not in cache:return
            import json
            details.configure(state='normal');details.delete('1.0','end')
            details.insert('1.0',json.dumps(cache[selected[0]],ensure_ascii=False,indent=2))
            details.configure(state='disabled')
        register_tree.bind('<<TreeviewSelect>>',inspect_action)
        def export_register():
            path=filedialog.asksaveasfilename(parent=dialog,defaultextension='.csv',filetypes=[('CSV','*.csv'),('JSON','*.json')])
            if not path:return
            try:export_action_register(store,path,format='json' if path.lower().endswith('.json') else 'csv',**params())
            except (ValueError,KeyError,OSError) as exc:messagebox.showerror('Export',str(exc),parent=dialog)
        ttk.Button(panel,text='Filtrer',command=reload).pack(side='left',padx=4)
        ttk.Button(panel,text='Exporter',command=export_register).pack(side='left',padx=4)
        ttk.Label(dialog,text='Statuts du registre audité · lecture seule · aucune décision de comité présumée').pack(pady=4)
        reload()
    ttk.Button(bar,text='Registre comité',command=open_action_register).pack(side='left',padx=3)
    def open_committee_tracking():
        from decision_committee_dashboard_v560 import committee_dashboard_v560, export_committee_dashboard
        try:
            dialog=tk.Toplevel(window)
            dialog.title('Suivi des décisions de comité — v5.60')
            dialog.geometry('1120x680')
            panel=ttk.Frame(dialog);panel.pack(fill='x',padx=8,pady=6)
            owner_var=tk.StringVar(value='')
            priority_var=tk.StringVar(value='ALL')
            deadline_var=tk.StringVar(value='ALL')
            verdict_var=tk.StringVar(value='ALL')
            ttk.Label(panel,text='Responsable').pack(side='left')
            ttk.Entry(panel,textvariable=owner_var,width=17).pack(side='left',padx=3)
            for title,var,options in [('Priorité',priority_var,('ALL','P1','P2','P3')),
                                      ('Échéance',deadline_var,('ALL','overdue','due_soon','upcoming','none')),
                                      ('Verdict',verdict_var,('ALL','APPROVE','REJECT','DEFER','UNREVIEWED'))]:
                ttk.Label(panel,text=title).pack(side='left',padx=3)
                ttk.Combobox(panel,textvariable=var,values=options,width=12,state='readonly').pack(side='left')
            frame=ttk.Frame(dialog);frame.pack(fill='both',expand=True,padx=8,pady=6)
            cols=('decision_id','owner','priority','due_date','deadline_state','committee_verdict','committee_actor','committee_meeting_date')
            tree=ttk.Treeview(frame,columns=cols,show='headings',height=14)
            for key in cols:tree.heading(key,text=key);tree.column(key,width=140,stretch=True)
            scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
            detail=tk.Text(dialog,height=9,wrap='word');detail.pack(fill='x',padx=8,pady=5)
            summary=tk.StringVar(value='')
            ttk.Label(dialog,textvariable=summary).pack(pady=4)
            cache={}
            def params():
                return {'owner':owner_var.get().strip() or None,'priority':priority_var.get(),
                        'deadline':deadline_var.get(),'verdict':verdict_var.get()}
            def reload():
                data=committee_dashboard_v560(store,**params())
                tree.delete(*tree.get_children());cache.clear()
                for i,item in enumerate(data['actions']):
                    key=str(i);cache[key]=item
                    tree.insert('','end',iid=key,values=[item.get(k) or '' for k in cols])
                detail.delete('1.0','end')
                summary.set(f"{data['total']} décisions · {data['overdue']} en retard · {data['deferred']} différées · {data['unreviewed']} sans résolution · audit {data['audit_head'][:12]}")
            def selected(_event=None):
                detail.delete('1.0','end')
                selection=tree.selection()
                if selection:
                    item=cache[selection[0]]
                    detail.insert('1.0',json.dumps({'history':item['committee_history'],
                      'expected_actions':item['expected_actions'],'missing_evidence':item['missing_evidence']},ensure_ascii=False,indent=2))
            tree.bind('<<TreeviewSelect>>',selected)
            def export():
                path=filedialog.asksaveasfilename(parent=dialog,defaultextension='.csv',filetypes=[('CSV','*.csv'),('JSON','*.json')])
                if not path:return
                try:export_committee_dashboard(store,path,format='json' if path.lower().endswith('.json') else 'csv',**params())
                except (ValueError,KeyError,OSError) as exc:messagebox.showerror('Export',str(exc),parent=dialog)
            ttk.Button(panel,text='Filtrer',command=reload).pack(side='left',padx=4)
            ttk.Button(panel,text='Exporter',command=export).pack(side='left',padx=4)
            ttk.Label(dialog,text='Lecture seule · filtres après contrôle complet · aucune activation en production').pack(pady=3)
            reload()
        except Exception as exc:
            messagebox.showerror('Suivi comité',str(exc),parent=window)
    ttk.Button(bar,text='Suivi comité',command=open_committee_tracking).pack(side='left',padx=3)



    ttk.Label(views_bar,text='Nom de la vue :').pack(side='left',padx=3)
    ttk.Entry(views_bar,textvariable=view_name,width=20).pack(side='left',padx=3)
    def save():
        try:saved.save(view_name.get(),filters());selected_view.set(view_name.get());update_choices()
        except (ValueError,OSError) as exc:messagebox.showerror('Vue',str(exc),parent=window)
    def apply():
        try:
            view=saved.load()[selected_view.get()]
            query.set(view['query']);owner.set(view['owner'] or '');status.set(view['status']);deadline.set(view['deadline']);refresh()
        except (ValueError,KeyError,OSError) as exc:messagebox.showerror('Vue',str(exc),parent=window)
    def remove():
        try:saved.delete(selected_view.get());selected_view.set('');update_choices()
        except (ValueError,KeyError,OSError) as exc:messagebox.showerror('Vue',str(exc),parent=window)
    ttk.Button(views_bar,text='Enregistrer vue',command=save).pack(side='left',padx=3)
    ttk.Button(views_bar,text='Charger vue',command=apply).pack(side='left',padx=3)
    ttk.Button(views_bar,text='Supprimer vue',command=remove).pack(side='left',padx=3)
    ttk.Label(views_bar,text='Vues existantes :').pack(side='left',padx=3)
    selected_view = tk.StringVar()
    choices=ttk.Combobox(views_bar,textvariable=selected_view,width=20,state='readonly')
    choices.pack(side='left',padx=3)
    def update_choices():
        try:choices['values']=tuple(sorted(saved.load()))
        except (ValueError,OSError) as exc:messagebox.showerror('Vues enregistrées',str(exc),parent=window)
    update_choices()
    # One workspace for reading and human decision actions; no second decision window.
    actions=ttk.LabelFrame(window,text='Actions humaines — décision sélectionnée',padding=8)
    actions.pack(fill='x',padx=10,pady=4)
    def selected_id():
        selection=tree.selection()
        return items[selection[0]]['id'] if selection and selection[0] in items else None
    def run_action(action):
        try:
            ident=selected_id()
            if action!='create' and not ident:
                messagebox.showinfo('Décision','Sélectionnez une décision',parent=window)
                return
            if action=='create':
                from decision_guided_forms_v607 import guided_decision_form
                values=guided_decision_form(window, title='Nouvelle décision')
                if values is None:return
                store.create(values['ident'],values['subject'],values['owner'],values['due_date'],values['evidence_reference'])
            elif action=='transition':
                from decision_guided_forms_v607 import guided_transition_form
                values=guided_transition_form(window)
                if values is None:return
                store.transition(ident,values['status'],values['actor'],values['rationale'],approval=values['approval'])
            elif action=='followup':
                actor=simpledialog.askstring('Relance','Auteur',parent=window)
                if actor is None:return
                note=simpledialog.askstring('Relance','Note',parent=window)
                if note is None:return
                store.followup(ident,actor,note)
            elif action=='link':
                if history is None:raise ValueError('chronologie indisponible')
                from campaign_timeline_v533 import timeline
                events=timeline(history)['events']
                if not events:raise ValueError('aucune alerte disponible')
                picker=tk.Toplevel(window)
                picker.title('Choisir une alerte vérifiée')
                picker.geometry('900x420')
                picker.transient(window)
                choices=ttk.Treeview(picker,columns=('code','earlier','later'),show='headings',selectmode='browse')
                for column,label in [('code','Code'),('earlier','Campagne avant'),('later','Campagne après')]:
                    choices.heading(column,text=label)
                    choices.column(column,width=230)
                choices.pack(fill='both',expand=True,padx=8,pady=8)
                for index,event in enumerate(events):
                    choices.insert('','end',iid=str(index),values=(event['code'],event['earlier_id'],event['later_id']))
                def accept():
                    selection=choices.selection()
                    if not selection:return
                    try:store.link_event(ident,events[int(selection[0])]);picker.destroy();refresh()
                    except (ValueError,KeyError,OSError) as exc:messagebox.showerror('Lien refusé',str(exc),parent=picker)
                ttk.Button(picker,text='Lier l’alerte sélectionnée',command=accept).pack(pady=6)
                return
            elif action=='qualify':
                if qualification_store is None:raise ValueError('registre de qualification indisponible')
                from decision_guided_forms_v607 import guided_qualification_form
                values=guided_qualification_form(window)
                if values is None:return
                qualification_store.qualify(ident,values['actor'],values['verdict'],values['criteria'],values['rationale'])
            elif action=='export':
                path=filedialog.asksaveasfilename(parent=window,defaultextension='.json',filetypes=[('JSON','*.json')])
                if not path:return
                store.export(path)
            refresh()
        except (ValueError,KeyError,OSError) as exc:
            messagebox.showerror('Gouvernance',str(exc),parent=window)
    for label,action in [('Créer','create'),('Changer statut','transition'),('Lier une alerte','link'),('Relance','followup'),('Qualifier preuves','qualify'),('Exporter + audit','export')]:
        ttk.Button(actions,text=label,command=lambda a=action:run_action(a)).pack(side='left',padx=4)
    # Explicit refresh avoids expensive database reads for every keystroke.
    refresh()
    return window
