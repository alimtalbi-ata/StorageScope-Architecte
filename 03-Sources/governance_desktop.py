"""StorageScope Governance desktop review console (Tkinter, Python stdlib)."""
from __future__ import annotations
import json
import re
import sqlite3
from pathlib import Path
from contextlib import closing
from governance_service import assess
from review_registry_v622 import decide, candidate_key, verify

def load_assessment(path):
    records=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(records,list): raise ValueError('Inventory must be a JSON array')
    return assess(records)

def eligible_candidates(report):
    """All proposals remain visible; blocked proposals are never actionable."""
    result=[]
    for i,c in enumerate(report['reconciliation']['candidates']):
        blocked=c.get('review_eligibility') == 'BLOCKED_CONTRADICTION'
        if blocked:
            key='BLOCKED:' + str(i)
        else:
            try: key=candidate_key(c)
            except (ValueError,TypeError,KeyError):
                key='INVALID:' + str(i)
                c={**c,'review_eligibility':'BLOCKED_CONTRADICTION'}
        result.append((key,c))
    return result

def parse_search(query):
    """Split case-insensitive terms; quoted phrases stay together.

    An incomplete quote is treated as ordinary text during interactive typing.
    """
    if not isinstance(query, str):
        raise TypeError("Search query must be text")
    return [m.group(1) if m.group(1) is not None else m.group(2)
            for m in re.finditer(r'"([^"]*)"|(\S+)', query.casefold())
            if (m.group(1) if m.group(1) is not None else m.group(2)).strip()]

def filter_candidates(candidates, query="", state="ALL"):
    """Multi-term AND search, preserving stable original indices.

    Prefixes asset:, key:, status: restrict a term to the relevant field.
    Other terms search the complete candidate. No mutation or automatic approval.
    """
    terms = parse_search(query)
    # Empty searches are common when paging large inventories: avoid JSON serialization.
    if not terms and state == "ALL":
        return [(i, key, candidate) for i, (key, candidate) in enumerate(candidates)]
    # Compile the query once, not once per inventory record.
    qualified = []
    general = []
    for term in terms:
        prefix, sep, value = term.partition(":")
        if sep and prefix in ("asset", "key", "status"):
            if not value:
                return []
            qualified.append((prefix, value))
        else:
            general.append(term)
    result = []
    for i, (key, candidate) in enumerate(candidates):
        eligibility = str(candidate.get("review_eligibility", "REVIEW_REQUIRED"))
        if state != "ALL" and eligibility != state:
            continue
        if not terms:
            result.append((i, key, candidate))
            continue
        key_text = str(key).casefold()
        status_text = eligibility.casefold()
        # Reject cheap key/status predicates before constructing asset text or JSON.
        if any((value not in key_text if field == "key" else
                value not in status_text if field == "status" else False)
               for field, value in qualified):
            continue
        assets = candidate.get("asset_ids") or []
        if not isinstance(assets, (list, tuple)):
            assets = [assets]
        asset_text = " ".join(map(str, assets)).casefold()
        if any(value not in asset_text for field, value in qualified if field == "asset"):
            continue
        if general:
            # Cheap fields may already satisfy every free-text predicate.
            # Only serialize the complete record when additional evidence is needed.
            short_text = key_text + " " + asset_text
            missing = [term for term in general if term not in short_text]
            if missing:
                full_text = short_text + " " + json.dumps(candidate, ensure_ascii=False, default=str).casefold()
                if any(term not in full_text for term in missing):
                    continue
        result.append((i, key, candidate))
    return result

def paginate_candidates(candidates, page=0, page_size=100):
    if not isinstance(page,int) or not isinstance(page_size,int) or page<0 or page_size<1 or page_size>1000:
        raise ValueError('Invalid page or page size')
    return candidates[page*page_size:(page+1)*page_size]

def page_bounds(total, page, page_size=100):
    """Clamp pagination safely after filters or inventory changes."""
    if not isinstance(total,int) or total<0 or not isinstance(page,int) or not isinstance(page_size,int) or page_size<1 or page_size>1000:
        raise ValueError("Invalid pagination arguments")
    last=max(0,(total-1)//page_size)
    return min(max(0,page),last),last

def page_summary(total, page, page_size=100):
    """Human-readable visible interval, including the empty-result case."""
    current, last = page_bounds(total, page, page_size)
    if total == 0:
        return "0 résultat · page 1/1"
    start = current * page_size + 1
    end = min(total, (current + 1) * page_size)
    return f"{start}–{end} sur {total} · page {current+1}/{last+1}"

def display_assets(candidate, max_chars=180):
    """Bound expensive/long tree cell text; full values remain in details."""
    values = candidate.get('asset_ids') or []
    if not isinstance(values, (list, tuple)):
        values = [values]
    text = ', '.join(map(str, values))
    return text if len(text) <= max_chars else text[:max_chars-1] + '…'

def can_decide(candidate):
    if not isinstance(candidate, dict):
        return False
    if candidate.get('review_eligibility') not in ('ELIGIBLE', 'REVIEW_REQUIRED'):
        return False
    if candidate.get('action') == 'BLOCKED' or candidate.get('risk') == 'HIGH':
        return False
    if any(candidate.get(k) for k in ('contradictions', 'identity_conflicts', 'identity_disagreements', 'blocking_reasons')):
        return False
    try:
        return bool(candidate.get('review_key')) and candidate['review_key'] == candidate_key(candidate)
    except (ValueError, TypeError, KeyError):
        return False


def explain_candidate(candidate):
    """Present recorded reconciliation facts without inventing a confidence score."""
    if not isinstance(candidate, dict):
        raise TypeError("Candidate must be a mapping")
    blocked = candidate.get('review_eligibility') == 'BLOCKED_CONTRADICTION'
    eligibility = str(candidate.get('review_eligibility', 'REVIEW_REQUIRED'))
    assets = candidate.get('asset_ids') or []
    if not isinstance(assets, (list, tuple)):
        assets = [assets]
    evidence = candidate.get('identity_evidence') or []
    if not isinstance(evidence, (list, tuple)):
        evidence = [evidence]
    evidence = [str(item) for item in evidence if item is not None]
    # Only fields explicitly present in the report are shown as evidence.
    conflict_fields = ('identity_conflicts', 'contradictions', 'conflicts', 'blocking_reasons')
    conflicts = {key: candidate[key] for key in conflict_fields if candidate.get(key)}
    if candidate.get('identity_disagreements'):
        conflicts['identity_disagreements'] = candidate['identity_disagreements']
    return {
        'status': eligibility,
        'risk': candidate.get('risk', 'UNASSESSED'),
        'same_source': candidate.get('same_source', False),
        'decision_allowed': can_decide(candidate),
        'assets': [str(asset) for asset in assets],
        'identity_evidence': evidence,
        'conflicts': conflicts,
        'reason': ('Contradiction d’identité : décision interdite.' if blocked else
                   'Proposition révisable uniquement après validation humaine.' if can_decide(candidate) else
                   'Décision indisponible : clé ou éligibilité insuffisante.'),
        'limitations': 'Aucun score de confiance calculé ; consulter les données source avant décision.',
    }

def read_audit_history(db_path, limit=100, candidate=None):
    """Read-only, bounded audit view; verify chain before showing decisions."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise ValueError("Invalid audit history limit")
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"Audit registry not found: {path}")
    validation = verify(path)
    if not validation['valid']:
        raise ValueError("Audit integrity verification failed")
    # SQLite URI mode=ro prevents accidental database creation or modification.
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as conn:
        if candidate is None:
            rows = conn.execute('SELECT seq,candidate_key,action,reviewer,at,event_hash FROM audit ORDER BY seq DESC LIMIT ?', (limit,)).fetchall()
        else:
            rows = conn.execute('SELECT seq,candidate_key,action,reviewer,at,event_hash FROM audit WHERE candidate_key=? ORDER BY seq DESC LIMIT ?', (candidate,limit)).fetchall()
    return [{'seq': r[0], 'candidate_key': r[1], 'action': r[2], 'reviewer': r[3], 'at': r[4], 'event_hash': r[5]} for r in rows]

def history_for_selection(db_path, selected_key=None, limit=100):
    """Restrict history to the exact selected review key; never use truncated labels."""
    if selected_key is not None and (not isinstance(selected_key, str) or not selected_key.strip()):
        raise ValueError("Invalid selected review key")
    return read_audit_history(db_path, limit=limit, candidate=selected_key)

def format_audit_event(event):
    """Readable audit detail; preserve exact identifiers and full SHA-256 hash."""
    required = ('seq', 'candidate_key', 'action', 'reviewer', 'at', 'event_hash')
    if not isinstance(event, dict) or any(key not in event for key in required):
        raise ValueError('Incomplete audit event')
    return ('ÉVÉNEMENT D’AUDIT — LECTURE SEULE\n'
            f"Séquence : {event['seq']}\nDate : {event['at']}\n"
            f"Décision : {event['action']}\nRéviseur : {event['reviewer']}\n"
            f"Clé complète : {event['candidate_key']}\n"
            f"Empreinte SHA-256 : {event['event_hash']}\n\n"
            'Intégrité locale vérifiée avant lecture ; absence d’ancrage externe.')

def benchmark_filter(candidates, queries, iterations=3):
    """Repeatable functional microbenchmark; no claims about Tkinter frame rate."""
    if not isinstance(iterations, int) or isinstance(iterations, bool) or not 1 <= iterations <= 100:
        raise ValueError('Invalid iteration count')
    from time import perf_counter
    samples = []
    for query in queries:
        start = perf_counter()
        count = 0
        for _ in range(iterations):
            count = len(filter_candidates(candidates, query))
        samples.append({'query': query, 'matched': count,
                        'mean_ms': round((perf_counter()-start)*1000/iterations, 3)})
    return samples

def reconcile_tree_rows(tree, rows):
    """Update a Treeview while preserving selection, viewport and stable item IDs.

    Benchmarks on a real Treeview favor rebuilding large pages over per-item
    reconciliation. Small pages retain incremental updates for low churn.
    """
    current = list(tree.get_children())
    incoming = [iid for iid, _ in rows]
    if len(incoming) != len(set(incoming)):
        raise ValueError("Duplicate Treeview item IDs")
    # For large pages, avoid O(n) item lookups, comparisons and move calls.
    # Small pages preserve the fast path for a single modified value.
    rebuild = len(rows) >= 500 or (current and len(current) == len(incoming)
                                  and sum(a != b for a, b in zip(current, incoming)) > len(incoming) // 4)
    if rebuild:
        selected = tuple(tree.selection()) if hasattr(tree, 'selection') else ()
        visible = tree.yview()[0] if hasattr(tree, 'yview') else None
        for iid in current:
            tree.delete(iid)
        for position, (iid, values) in enumerate(rows):
            tree.insert('', position, iid=iid, values=values)
        if selected and hasattr(tree, 'selection_set'):
            tree.selection_set(tuple(iid for iid in selected if tree.exists(iid)))
        if visible is not None and hasattr(tree, 'yview_moveto'):
            tree.yview_moveto(visible)
        return
    expected = set(incoming)
    for iid in current:
        if iid not in expected:
            tree.delete(iid)
    current_order = list(tree.get_children())
    for position, (iid, values) in enumerate(rows):
        if tree.exists(iid):
            if tuple(tree.item(iid, 'values')) != tuple(str(v) for v in values):
                tree.item(iid, values=values)
            if current_order[position] != iid:
                tree.move(iid, '', position)
                current_order.remove(iid)
                current_order.insert(position, iid)
        else:
            tree.insert('', position, iid=iid, values=values)
            current_order.insert(position, iid)


def launch(parent=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    root=tk.Toplevel(parent) if parent is not None else tk.Tk()
    root.title('StorageScope — Gouvernance / Revue humaine v6.86')
    root.geometry('1100x720')
    if parent is not None:
        root.transient(parent)

    report_state={'report':None,'candidates':[],'page':0,'matched':[]}
    inventory=tk.StringVar(); db=tk.StringVar(value=str(Path.home()/'storagescope-review.sqlite'))
    reviewer=tk.StringVar(); reason=tk.StringVar(); status=tk.StringVar(value='REJECTED')
    header=ttk.Frame(root,padding=10);header.pack(fill='x')
    ttk.Label(header,text='Inventaire JSON').grid(row=0,column=0,sticky='w')
    ttk.Entry(header,textvariable=inventory,width=95).grid(row=0,column=1,sticky='ew')
    def browse():
        p=filedialog.askopenfilename(filetypes=[('JSON','*.json')]);
        if p: inventory.set(p)
    ttk.Button(header,text='Parcourir',command=browse).grid(row=0,column=2)
    ttk.Label(header,text='Registre SQLite').grid(row=1,column=0,sticky='w')
    ttk.Entry(header,textvariable=db,width=95).grid(row=1,column=1,sticky='ew')
    header.columnconfigure(1,weight=1)
    summary=tk.StringVar(value='Chargez un inventaire pour commencer.');ttk.Label(root,textvariable=summary,padding=10).pack(anchor='w')
    filters=ttk.Frame(root,padding=(10,2));filters.pack(fill='x')
    query=tk.StringVar(); state_filter=tk.StringVar(value='ALL')
    ttk.Label(filters,text='Rechercher (mots, asset:, key:, status:)' ).pack(side='left')
    search_entry=ttk.Entry(filters,textvariable=query,width=45);search_entry.pack(side='left',padx=5)
    def focus_search(event=None):
        search_entry.focus_set()
        search_entry.select_range(0, 'end')
        return 'break'
    root.bind('<Control-f>', focus_search)
    ttk.Label(filters,text='Statut').pack(side='left')
    ttk.Combobox(filters,textvariable=state_filter,values=['ALL','REVIEW_REQUIRED','BLOCKED_CONTRADICTION'],state='readonly',width=23).pack(side='left',padx=5)
    pager=ttk.Frame(root,padding=(10,2));pager.pack(fill='x')
    page_label=tk.StringVar(value='Page 1');ttk.Label(pager,textvariable=page_label).pack(side='left')
    table=ttk.Treeview(root,columns=('key','assets','status'),show='headings',height=13)
    for name,width in [('key',270),('assets',530),('status',180)]:table.heading(name,text=name);table.column(name,width=width)
    table_frame=ttk.Frame(root,padding=(10,0,10,0));table_frame.pack(fill='both',expand=True)
    table.pack(in_=table_frame,side='left',fill='both',expand=True)
    table_scroll=ttk.Scrollbar(table_frame,orient='vertical',command=table.yview)
    table_scroll.pack(side='right',fill='y');table.configure(yscrollcommand=table_scroll.set)
    details_frame=ttk.Frame(root,padding=(10,5,10,5));details_frame.pack(fill='both',expand=True)
    details=tk.Text(details_frame,height=8,wrap='word',state='disabled')
    details.pack(side='left',fill='both',expand=True)
    details_scroll=ttk.Scrollbar(details_frame,orient='vertical',command=details.yview)
    details_scroll.pack(side='right',fill='y');details.configure(yscrollcommand=details_scroll.set)
    def set_details(content):
        details.configure(state='normal')
        details.delete('1.0','end')
        if content: details.insert('1.0',content)
        details.configure(state='disabled')
    def selected(event=None):
        s=table.selection();set_details('')
        if s:
            idx=int(s[0])
            if 0 <= idx < len(report_state['candidates']):
                set_details('EXPLICATION / PREUVES\n' + json.dumps(explain_candidate(report_state['candidates'][idx][1]),indent=2,ensure_ascii=False) + '\n\nDONNÉES SOURCE\n' + json.dumps(report_state['candidates'][idx][1],indent=2,ensure_ascii=False))
    table.bind('<<TreeviewSelect>>',selected)
    def refresh(*args, refilter=True):
        if refilter:
            report_state['matched'] = filter_candidates(report_state['candidates'],query.get(),state_filter.get())
        matched=report_state['matched']
        total=len(matched)
        report_state['page'],max_page=page_bounds(total,report_state['page'])
        page_label.set(page_summary(total,report_state['page']))
        previous_button.configure(state='normal' if report_state['page'] > 0 else 'disabled')
        next_button.configure(state='normal' if report_state['page'] < max_page else 'disabled')
        rows = [(str(i), (key if len(key)<=36 else key[:35]+'…', display_assets(c), c.get('review_eligibility','REVIEW_REQUIRED'))) for i,key,c in paginate_candidates(matched,report_state['page'])]
        reconcile_tree_rows(table, rows)
        selected()  # Re-render details for the retained selection; clear if no longer present.
        summary.set(f'{len(matched)} trouvée(s) sur {len(report_state["candidates"])} proposition(s), conflits bloqués inclus. Aucune fusion automatique.')
    def change_page(delta):
        current, last = page_bounds(len(report_state['matched']), report_state['page'])
        next_page = min(last, max(0, current + delta))
        if next_page == current:
            return  # No needless Treeview rebuild at page boundaries.
        report_state['page'] = next_page
        # Pagination must reuse the existing filtered snapshot.
        refresh(refilter=False)
    previous_button=ttk.Button(pager,text='Précédent',command=lambda:change_page(-1))
    previous_button.pack(side='left',padx=6)
    next_button=ttk.Button(pager,text='Suivant',command=lambda:change_page(1))
    next_button.pack(side='left')
    def navigate_from_table(event, delta):
        change_page(delta)
        return 'break'
    table.bind('<Prior>', lambda event: navigate_from_table(event, -1))
    table.bind('<Next>', lambda event: navigate_from_table(event, 1))
    def reset_page(*args):
        report_state['page']=0;refresh()
    # Debounce typing: avoid rebuilding the tree on every keystroke in large inventories.
    pending_refresh={'id':None}
    def schedule_refresh(*args):
        if pending_refresh['id'] is not None:
            root.after_cancel(pending_refresh['id'])
        pending_refresh['id']=root.after(180,apply_refresh)
    def apply_refresh():
        pending_refresh['id']=None
        reset_page()
    query.trace_add('write',schedule_refresh)
    state_filter.trace_add('write',reset_page)
    def load():
        if pending_refresh['id'] is not None:
            root.after_cancel(pending_refresh['id'])
            pending_refresh['id']=None
        try:
            report=load_assessment(inventory.get());candidates=eligible_candidates(report)
            report_state.update(report=report,candidates=candidates,page=0)
            refresh()
        except Exception as e:messagebox.showerror('Erreur de chargement',str(e))
    ttk.Button(header,text='Analyser',command=load).grid(row=0,column=3,padx=4)
    actions=ttk.Frame(root,padding=10);actions.pack(fill='x')
    ttk.Label(actions,text='Réviseur').pack(side='left');ttk.Entry(actions,textvariable=reviewer,width=18).pack(side='left',padx=5)
    ttk.Label(actions,text='Justification').pack(side='left');ttk.Entry(actions,textvariable=reason,width=40).pack(side='left',padx=5)
    ttk.Combobox(actions,textvariable=status,values=['REJECTED','APPROVED'],state='readonly',width=12).pack(side='left')
    def submit():
        sel=table.selection()
        if not sel:messagebox.showwarning('Sélection','Sélectionnez une proposition');return
        idx=int(sel[0])
        if not 0 <= idx < len(report_state['candidates']):
            messagebox.showerror('Sélection périmée','Rechargez les propositions avant de décider.')
            return
        candidate=report_state['candidates'][idx][1]
        if not can_decide(candidate):
            messagebox.showerror('Action interdite','Proposition bloquée ou identité invalide : consultation uniquement.')
            return
        if not messagebox.askyesno('Confirmation',f'Enregistrer {status.get()} ? Cette décision est irréversible et ne fusionne aucune donnée.') :return
        try:
            key,_=report_state['candidates'][idx]
            outcome=decide(db.get(),report_state['report'],key,status.get(),reviewer.get(),reason.get())
            messagebox.showinfo('Décision enregistrée',f"Audit : {outcome['audit_hash']}")
            refresh()
        except Exception as e:messagebox.showerror('Décision refusée',str(e))
    ttk.Button(actions,text='Enregistrer la décision',command=submit).pack(side='left',padx=5)
    def audit():
        try:messagebox.showinfo('Vérification audit',json.dumps(verify(db.get()),indent=2))
        except Exception as e:messagebox.showerror('Audit indisponible',str(e))
    ttk.Button(actions,text='Vérifier audit',command=audit).pack(side='left',padx=5)
    def history():
        try:
            selection=table.selection()
            selected_key=None
            if selection:
                idx=int(selection[0])
                if not 0 <= idx < len(report_state['candidates']):
                    raise ValueError('Sélection périmée')
                selected_key=report_state['candidates'][idx][0]
            rows=history_for_selection(db.get(), selected_key=selected_key, limit=100)
            dialog=tk.Toplevel(root);dialog.title('Historique des décisions — lecture seule')
            dialog.geometry('920x480');dialog.transient(root)
            ttk.Label(dialog,text=f'{len(rows)} décision(s) · '+('proposition sélectionnée' if selected_key else 'toutes propositions')+' · chaîne vérifiée · lecture seule',padding=8).pack(anchor='w')
            view=ttk.Treeview(dialog,columns=('seq','at','action','reviewer','key'),show='headings')
            for name,width in [('seq',60),('at',210),('action',100),('reviewer',140),('key',360)]:
                view.heading(name,text=name);view.column(name,width=width)
            for pos,row in enumerate(rows):
                view.insert('', 'end',iid=str(pos),values=(row['seq'],row['at'],row['action'],row['reviewer'],row['candidate_key']))
            view.pack(fill='both',expand=True,padx=8,pady=8)
            detail=tk.Text(dialog,height=7,wrap='word',state='disabled')
            detail.pack(fill='x',padx=8,pady=(0,5))
            def show_event(event=None):
                selection=view.selection()
                detail.configure(state='normal');detail.delete('1.0','end')
                if selection:
                    detail.insert('1.0',format_audit_event(rows[int(selection[0])]))
                detail.configure(state='disabled')
            view.bind('<<TreeviewSelect>>',show_event)
            view.selection_set(view.get_children()[0]) if rows else None
            show_event()
            ttk.Label(dialog,text='Chaîne SHA-256 locale non ancrée à une preuve externe.',padding=8).pack(anchor='w')
        except Exception as exc:
            messagebox.showerror('Historique indisponible',str(exc))
    ttk.Button(actions,text='Historique (sélection)',command=history).pack(side='left',padx=5)
    if parent is None:
        root.mainloop()
if __name__=='__main__':launch()
