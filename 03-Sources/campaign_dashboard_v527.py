"""Read-only benchmark dashboard for the standalone StorageScope prototype.
Author: Abdelhalim Talbi.
"""
import json
from statistics import median
from pathlib import Path
from campaign_history_v526 import CampaignHistory


def dashboard_data(history, *, nodes=None, edits=None, spacing=None, limit=100):
    """Return an auditable view; filtered results never authorize policy changes."""
    for value in (nodes, edits, spacing):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError('invalid category filter')
    records = history.list(limit)
    series = []
    for record in records:
        pairs = record['campaign']['pairs']
        chosen = [p for p in pairs if (nodes is None or p['nodes'] == nodes)
                  and (edits is None or p['edits'] == edits)
                  and (spacing is None or p['spacing'] == spacing)]
        if not chosen:
            continue
        gains = [(p['baseline_seconds'] - p['candidate_seconds']) / p['baseline_seconds']
                 for p in chosen]
        series.append({'id': record['id'], 'recorded_at': record['recorded_at'],
                       'sha256': record['sha256'], 'pairs': len(chosen),
                       'median_gain': median(gains), 'min_gain': min(gains),
                       'max_gain': max(gains),
                       'regressions': sum(g < -.10 for g in gains),
                       'routes_mismatch': sum(p['routes_equal'] is not True for p in chosen)})
    # Safety gate must always use unfiltered campaigns; filtered trends are descriptive only.
    overall = history.report(limit)
    return {'filters': {'nodes': nodes, 'edits': edits, 'spacing': spacing},
            'campaigns': series, 'displayed_count': len(series),
            'overall_gate': {'selected_policy': overall['selected_policy'],
                             'reason': overall['reason'], 'alerts': overall['alerts']},
            'recommendation_only': True, 'production_activation': False,
            'filter_is_descriptive_only': True}


def export_dashboard(history, destination, **filters):
    result = dashboard_data(history, **filters)
    Path(destination).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def launch_dashboard(db_path, *, parent=None):
    """Optional Tk UI; importable in headless environments without starting Tk."""
    import tkinter as tk
    from tkinter import ttk, messagebox
    history = CampaignHistory(db_path)
    embedded = parent is not None
    root = parent if embedded else tk.Tk()
    if not embedded:
        root.title('StorageScope | Campagnes et benchmarks')
        root.geometry('1120x850')
        root.minsize(760, 460)
    # Three task-oriented tabs replace the previous vertically overloaded page.
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=8, pady=6)
    history_tab = ttk.Frame(notebook)
    comparison_tab = ttk.Frame(notebook)
    review_tab = ttk.Frame(notebook)
    notebook.add(history_tab, text='Historique')
    notebook.add(comparison_tab, text='Comparer et exporter')
    notebook.add(review_tab, text='Alertes et revue')
    controls = ttk.LabelFrame(history_tab, text='1 · Filtres et actualisation', padding=12)
    controls.pack(fill='x')
    fields = {}
    for name in ('nodes', 'edits', 'spacing'):
        ttk.Label(controls, text={'nodes': 'Nœuds', 'edits': 'Modifications', 'spacing': 'Espacement'}[name]).pack(side='left', padx=4)
        var = tk.StringVar()
        entry = ttk.Entry(controls, textvariable=var, width=9)
        entry.pack(side='left', padx=4)
        entry.bind('<Return>', lambda event: refresh())
        fields[name] = var
    status = tk.StringVar(value='Lecture seule — aucune activation en production')
    ttk.Label(history_tab, textvariable=status, padding=8).pack(fill='x')
    table = ttk.Treeview(history_tab, columns=('date','count','median','regressions','mismatch'), show='headings', height=10)
    for key, title, width in [('date','Date UTC',210),('count','Paires',90),('median','Gain médian',120),('regressions','Régressions',110),('mismatch','Divergences',110)]:
        table.heading(key, text=title)
        table.column(key, width=width)
    table_frame = ttk.Frame(history_tab)
    table_frame.pack(fill='both', expand=True, padx=12)
    table_frame.columnconfigure(0, weight=1)
    table_frame.rowconfigure(0, weight=1)
    table.grid(in_=table_frame, row=0, column=0, sticky='nsew')
    vscroll = ttk.Scrollbar(table_frame, orient='vertical', command=table.yview)
    vscroll.grid(row=0, column=1, sticky='ns')
    hscroll = ttk.Scrollbar(table_frame, orient='horizontal', command=table.xview)
    hscroll.grid(row=1, column=0, sticky='ew')
    table.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
    for col in table['columns']:
        table.column(col, stretch=True, minwidth=85)
    canvas = tk.Canvas(history_tab, height=180, bg='#ffffff', highlightthickness=1)
    canvas.pack(fill='x', padx=12, pady=8)
    def refresh():
        try:
            filt = {k: (int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            data = dashboard_data(history, **filt)
        except (ValueError, KeyError) as exc:
            messagebox.showerror('Filtres / données', str(exc)); return
        table.delete(*table.get_children())
        for c in data['campaigns']:
            table.insert('', 'end', text=c['id'], values=(c['recorded_at'], c['pairs'],
                         f"{c['median_gain']:+.1%}", c['regressions'], c['routes_mismatch']))
        gate = data['overall_gate']
        status.set(f"Politique globale : {gate['selected_policy']} | {gate['reason']} | "
                   f"{data['displayed_count']} campagnes affichées | lecture seule")
        canvas.delete('all')
        w = max(canvas.winfo_width(), 740); h = 180
        canvas.create_line(45, h//2, w-20, h//2, fill='#999', dash=(3,3))
        points = data['campaigns']
        if not points: canvas.create_text(w//2, h//2, text='Aucune campagne pour ces filtres'); return
        max_abs = max(.05, max(abs(p['median_gain']) for p in points))
        step = (w-80)/max(len(points), 1)
        for i,p in enumerate(points):
            x=50+i*step+step/2
            y=h/2-p['median_gain']/max_abs*(h*.38)
            canvas.create_line(x,h/2,x,y,fill='#2563eb' if p['median_gain']>=0 else '#b91c1c',width=max(3,min(18,step*.55)))
            if len(points)<=15: canvas.create_text(x,h-12,text=p['id'][:12],font=('Arial',8))
    ttk.Button(controls, text='Actualiser', command=refresh).pack(side='left', padx=12)
    ttk.Button(controls, text='Effacer les filtres', command=lambda: ([(v.set('')) for v in fields.values()], refresh())).pack(side='left', padx=4)
    comparison = ttk.LabelFrame(comparison_tab, text='2 · Comparaison et exports', padding=8)
    comparison.pack(fill='x')
    ttk.Label(comparison, text='Campagnes à comparer (ID)').pack(side='left')
    first = tk.StringVar(); second = tk.StringVar()
    first_choice = ttk.Combobox(comparison, textvariable=first, width=18, state='readonly')
    second_choice = ttk.Combobox(comparison, textvariable=second, width=18, state='readonly')
    first_choice.pack(side='left', padx=4)
    second_choice.pack(side='left', padx=4)
    def reload_campaigns():
        try:
            ids = [r['id'] for r in history.list(10000)]
            first_choice['values'] = ids
            second_choice['values'] = ids
            if first.get() not in ids: first.set(ids[0] if ids else '')
            if second.get() not in ids: second.set(ids[-1] if len(ids)>1 else '')
        except ValueError as exc:
            messagebox.showerror('Historique', str(exc))
    ttk.Button(comparison, text='Recharger', command=reload_campaigns).pack(side='left', padx=4)

    detail = tk.StringVar(value='Sélectionnez deux campagnes pour comparer les mesures.')
    def compare_selected():
        try:
            from campaign_compare_v528 import compare_campaigns
            filters = {k: (int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            result = compare_campaigns(history, first.get().strip(), second.get().strip(), **filters)
            a,b = result['campaigns']
            delta = result['delta_median_gain']
            detail.set(f"{a['id']}: {a['sample_count']} mesures | {b['id']}: {b['sample_count']} mesures | "
                       + (f'Variation de gain médian : {delta:+.2%}' if delta is not None else 'Données filtrées insuffisantes'))
        except (ValueError, KeyError) as exc:
            messagebox.showerror('Comparaison', str(exc))
    ttk.Button(comparison, text='Comparer', command=compare_selected).pack(side='left', padx=8)
    ttk.Label(comparison_tab, textvariable=detail, padding=6).pack(fill='x')
    # v5.29: visual comparison and evidence drill-down (read-only).
    overlay = tk.Canvas(comparison_tab, height=190, bg='#ffffff', highlightthickness=0)
    overlay.pack(fill='x', padx=12)
    evidence = ttk.Treeview(comparison_tab, columns=('first','second','delta'), show='tree headings', height=5)
    evidence.heading('#0', text='ID mesure'); evidence.column('#0', width=160)
    for col, title in (('first','Gain A'),('second','Gain B'),('delta','Écart B−A')):
        evidence.heading(col,text=title); evidence.column(col,width=130)
    evidence.pack(fill='both', padx=12, pady=4)
    def visualize_selected():
        try:
            from campaign_visual_v529 import overlay_data, draw_overlay
            filters = {k: (int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            result = overlay_data(history, first.get().strip(), second.get().strip(), **filters)
            draw_overlay(overlay, result, width=max(740,overlay.winfo_width()))
            evidence.delete(*evidence.get_children())
            for point in result['points']:
                fmt=lambda v: '—' if v is None else f'{v:+.2%}'
                evidence.insert('', 'end', text=point['id'], values=tuple(fmt(point[k]) for k in ('first_gain','second_gain','delta')))
            status.set(f"{result['matched_count']} mesures appariées | {result['unmatched_count']} non appariées | contrôle global inchangé")
        except (ValueError, KeyError) as exc:
            messagebox.showerror('Visualisation',str(exc))
    ttk.Button(comparison,text='Superposer / preuves',command=visualize_selected).pack(side='left',padx=5)
    def export_selected():
        from tkinter import filedialog
        from campaign_report_v530 import export_report
        formats = [('JSON', '*.json'), ('CSV', '*.csv'), ('Markdown', '*.md')]
        path = filedialog.asksaveasfilename(title='Exporter la comparaison', defaultextension='.json', filetypes=formats)
        if not path: return
        ext = Path(path).suffix.lower().lstrip('.')
        try:
            filters = {k: (int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            info = export_report(history, first.get(), second.get(), path, format=ext, **filters)
            status.set(f"Export {info['format']} : SHA-256 {info['sha256'][:16]}…")
        except (ValueError, OSError) as exc:
            messagebox.showerror('Export', str(exc))
    from pathlib import Path
    ttk.Button(comparison, text='Exporter JSON / CSV / MD', command=export_selected).pack(side='left', padx=4)
    # v5.31: KPI summary and evidence drill-down; never changes the global gate.
    kpi_text = tk.StringVar(value='KPI : sélectionnez deux campagnes et cliquez sur Synthèse')
    ttk.Label(comparison_tab, textvariable=kpi_text, padding=8).pack(fill='x')
    selected_kpis = {'data': None}
    def show_kpis():
        try:
            from campaign_kpi_v531 import comparison_kpis
            filters = {k: (int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            data = comparison_kpis(history, first.get().strip(), second.get().strip(), **filters)
            selected_kpis['data'] = data
            alerts = ', '.join(a['code'] for a in data['alerts']) or 'aucune'
            delta = 'n/d' if data['median_delta'] is None else f"{data['median_delta']:+.2%}"
            kpi_text.set(f"Appariées {data['matched']} | Améliorées {data['improved']} | "
                         f"Dégradées {data['degraded']} | Non appariées {data['unmatched']} | "
                         f"Δ médiane {delta} | Alertes : {alerts}")
        except (ValueError, KeyError) as exc:
            messagebox.showerror('Synthèse', str(exc))
    ttk.Button(comparison, text='Synthèse KPI', command=show_kpis).pack(side='left', padx=4)
    def inspect_evidence(_event=None):
        selection = evidence.selection()
        if not selection: return
        try:
            from campaign_kpi_v531 import evidence_for_point
            if selected_kpis['data'] is None: show_kpis()
            if selected_kpis['data'] is None: return
            item = evidence.item(selection[0])
            detail = evidence_for_point(selected_kpis['data'], item['text'])
            messagebox.showinfo('Preuve de mesure (lecture seule)', json.dumps(detail, indent=2, ensure_ascii=False))
        except (ValueError, KeyError) as exc:
            messagebox.showerror('Preuve', str(exc))
    evidence.bind('<Double-1>', inspect_evidence)
    # v5.32: interactive severity filtering and evidence navigation.
    alert_controls = ttk.Frame(review_tab, padding=6)
    alert_controls.pack(fill='x')
    ttk.Label(alert_controls, text='Criticité des alertes').pack(side='left', padx=5)
    severity = tk.StringVar(value='all')
    ttk.Combobox(alert_controls, textvariable=severity, values=('all','critical','warning','info'),
                 state='readonly', width=12).pack(side='left')
    alert_table = ttk.Treeview(review_tab, columns=('severity','count','coverage'), show='tree headings', height=4)
    alert_table.heading('#0',text='Alerte')
    for col, title in (('severity','Criticité'),('count','Nombre'),('coverage','Preuves')):
        alert_table.heading(col,text=title)
    alert_table.pack(fill='x', padx=12, pady=3)
    alert_cache = {'view':None}
    def refresh_alerts():
        try:
            from campaign_alerts_v532 import alert_view
            filters = {k: (int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            view = alert_view(history, first.get(), second.get(), severity=severity.get(), **filters)
            alert_cache['view'] = view
            alert_table.delete(*alert_table.get_children())
            for a in view['alerts']:
                parent=alert_table.insert('', 'end', text=a['code'],
                    values=(a['severity'],a['count'],a['evidence_coverage']))
                for pid in a['evidence_ids']:
                    alert_table.insert(parent,'end',text=pid,values=('preuve','',''))
        except (ValueError,KeyError) as exc:
            messagebox.showerror('Alertes',str(exc))
    def open_alert_proof(_event=None):
        item=alert_table.focus()
        if not item or not alert_cache['view']: return
        parent=alert_table.parent(item)
        if not parent: return
        try:
            from campaign_alerts_v532 import alert_evidence
            result=alert_evidence(alert_cache['view'],alert_table.item(parent,'text'),alert_table.item(item,'text'))
            messagebox.showinfo('Preuve liée',json.dumps(result,indent=2,ensure_ascii=False))
        except (ValueError,KeyError) as exc:
            messagebox.showerror('Preuve',str(exc))
    ttk.Button(alert_controls,text='Afficher les alertes',command=refresh_alerts).pack(side='left',padx=8)
    alert_table.bind('<Double-1>',open_alert_proof)

    # v5.33: architecture-review timeline, read-only and global-gate independent.
    def show_timeline():
        try:
            from campaign_timeline_v533 import timeline
            from campaign_review_v534 import timeline_plot
            filters = {k: (int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            report = timeline(history, severity=severity.get(), **filters)
            plot = timeline_plot(report)
            popup = tk.Toplevel(root)
            popup.title('Chronologie graphique — lecture seule')
            popup.geometry('1020x650')
            chart = tk.Canvas(popup, width=900, height=270, bg='white')
            chart.pack(fill='x', padx=10, pady=8)
            chart.create_line(40,225,875,225,fill='#64748b')
            chart.create_text(80,15,text='Nombre d’occurrences par alerte',anchor='w')
            for p in plot['points']:
                chart.create_line(p['x'],225,p['x'],p['y'],fill=p['color'],width=7)
                chart.create_oval(p['x']-5,p['y']-5,p['x']+5,p['y']+5,fill=p['color'])
            columns=('date','type','severity','count','coverage')
            tree=ttk.Treeview(popup,columns=columns,show='headings',height=11)
            for key,title in [('date','Date UTC'),('type','Régression'),('severity','Criticité'),('count','Occurrences'),('coverage','Couverture')]:
                tree.heading(key,text=title)
                tree.column(key,width=160)
            tree.pack(fill='both',expand=True,padx=10,pady=8)
            for i,event in enumerate(report['events']):
                tree.insert('', 'end', iid=str(i),values=(event['recorded_at'],event['code'],event['severity'],event['count'],event['coverage']))
            def inspect_event(_event=None):
                selected=tree.selection()
                if not selected: return
                event=report['events'][int(selected[0])]
                proof={'event':event,'global_gate':report['overall_gate'],
                       'note':'Empreintes des campagnes ; preuves individuelles disponibles via Alertes.'}
                detail=tk.Toplevel(popup)
                detail.title('Événement et traçabilité')
                detail.geometry('800x450')
                widget=tk.Text(detail,wrap='word')
                widget.pack(fill='both',expand=True)
                widget.insert('1.0',json.dumps(proof,ensure_ascii=False,indent=2))
                widget.configure(state='disabled')
            tree.bind('<Double-1>',inspect_event)
            ttk.Label(popup,text='Double-clic sur une alerte : événements et empreintes SHA-256. Lecture seule.').pack(pady=6)
        except (ValueError, KeyError) as exc:
            messagebox.showerror('Chronologie', str(exc))
    def export_dossier_ui():
        try:
            from campaign_review_v534 import review_dossier
            path=filedialog.asksaveasfilename(defaultextension='.zip',filetypes=[('Dossier de revue ZIP','*.zip')])
            if not path: return
            filters={k:(int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            result=review_dossier(history,path,severity=severity.get(),**filters)
            messagebox.showinfo('Dossier de revue',f"Dossier exporté : {result['path']}")
        except (ValueError,KeyError,OSError) as exc:
            messagebox.showerror('Dossier de revue',str(exc))
    def export_timeline_ui():
        try:
            from campaign_timeline_v533 import export_timeline
            path = filedialog.asksaveasfilename(defaultextension='.md',
                filetypes=[('Markdown','*.md'),('JSON','*.json'),('CSV','*.csv')])
            if not path: return
            ext = path.rsplit('.',1)[-1].lower()
            fmt = 'md' if ext == 'md' else ext
            filters = {k: (int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            result = export_timeline(history,path,format=fmt,severity=severity.get(),**filters)
            messagebox.showinfo('Export de revue', f"Rapport créé : {result['path']}")
        except (ValueError,KeyError,OSError) as exc:
            messagebox.showerror('Export de revue',str(exc))
    ttk.Button(alert_controls,text='Chronologie',command=show_timeline).pack(side='left',padx=5)
    ttk.Button(alert_controls,text='Exporter revue',command=export_timeline_ui).pack(side='left',padx=5)

    ttk.Button(alert_controls,text='Dossier ZIP',command=export_dossier_ui).pack(side='left',padx=5)
    def show_executive():
        try:
            from campaign_timeline_v533 import timeline
            from campaign_executive_v535 import executive_summary, decision_register
            filters={k:(int(v.get()) if v.get().strip() else None) for k,v in fields.items()}
            summary=executive_summary(timeline(history,severity=severity.get(),**filters))
            detail=tk.Toplevel(root)
            detail.title('Synthèse exécutive et décisions — lecture seule')
            detail.geometry('850x600')
            notebook=ttk.Notebook(detail)
            notebook.pack(fill='both',expand=True)
            for title,payload in [('Synthèse',summary),('Registre (modèle)',decision_register(summary))]:
                page=ttk.Frame(notebook)
                notebook.add(page,text=title)
                widget=tk.Text(page,wrap='word')
                widget.pack(fill='both',expand=True)
                widget.insert('1.0',json.dumps(payload,ensure_ascii=False,indent=2))
                widget.configure(state='disabled')
        except (ValueError,KeyError,OSError) as exc:
            messagebox.showerror('Synthèse exécutive',str(exc))
    ttk.Button(alert_controls,text='Synthèse exécutive',command=show_executive).pack(side='left',padx=5)


    # v5.44: a single governance entry point, shared by reading and human actions.
    def show_governance_workspace():
        from decision_governance_v537 import GovernanceStore
        from decision_workspace_ui_v543 import open_workspace
        store = GovernanceStore(str(db_path) + '.architecture-decisions.sqlite')
        open_workspace(root, store, str(db_path) + '.governance-views.json', history=history)
    ttk.Button(alert_controls, text='Gouvernance', command=show_governance_workspace).pack(side='left', padx=5)

    root.after(100, reload_campaigns)
    root.after(150, refresh)
    if not embedded:
        root.mainloop()
    return root


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Read-only StorageScope benchmark dashboard')
    parser.add_argument('database', help='Path to SQLite history')
    parser.add_argument('--export', help='Export JSON without launching UI')
    args = parser.parse_args()
    if args.export: export_dashboard(CampaignHistory(args.database), args.export)
    else: launch_dashboard(args.database)
