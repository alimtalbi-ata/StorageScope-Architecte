"""StorageScope Windows desktop shell. Author: Abdelhalim Talbi."""
import os
import sys
import subprocess
import shutil
import sqlite3
from contextlib import closing
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from storage_risk_desktop_v6196 import assess_topology_file, format_risk_report, export_risk_report
from cmdb_review_desktop_v6198 import review_cmdb_file, format_cmdb_report, export_cmdb_report

APP_NAME = 'StorageScope'
VERSION = '6.108'


def user_data_dir(environ=None):
    env = os.environ if environ is None else environ
    base = env.get('LOCALAPPDATA') or env.get('APPDATA')
    return Path(base) / APP_NAME if base else Path.home() / '.storagescope'


def application_paths(root=None):
    base = Path(root) if root is not None else user_data_dir()
    base.mkdir(parents=True, exist_ok=True)
    return {'base': base, 'campaigns': base / 'campaigns.sqlite',
            'decisions': base / 'architecture-decisions.sqlite',
            'views': base / 'governance-views.json',
            'preferences': base / 'ui-preferences.json'}


def database_health(path):
    """Read-only integrity probe; never create a missing database."""
    path = Path(path)
    if not path.exists():
        return 'ABSENTE'
    uri = path.resolve().as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True, timeout=2)) as connection:
        result = connection.execute('PRAGMA quick_check').fetchone()[0]
    return 'OK' if result == 'ok' else 'ERREUR: ' + str(result)


def backup_databases(paths, destination):
    """Consistent SQLite backup, without copying active WAL files."""
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    if dest.resolve() == Path(paths['base']).resolve():
        raise ValueError('Le dossier de sauvegarde doit être distinct des données actives')
    created = []
    for name in ('decisions', 'campaigns'):
        source = Path(paths[name])
        if not source.exists():
            continue
        target = dest / source.name
        if source.resolve() == target.resolve():
            raise ValueError('La sauvegarde ne peut écraser la base active')
        with closing(sqlite3.connect(str(source), timeout=5)) as db:
            with closing(sqlite3.connect(str(target), timeout=5)) as output:
                db.backup(output)
        created.append(target)
    views = Path(paths['views'])
    if views.exists():
        target = dest / views.name
        if views.resolve() == target.resolve():
            raise ValueError('La sauvegarde ne peut écraser les vues actives')
        shutil.copy2(views, target)
        created.append(target)
    return created


def backup_snapshot(paths, destination):
    """Create a non-overwriting, verified snapshot in a new subdirectory.

    Returns (snapshot_directory, files). Incomplete snapshots are removed on failure.
    """
    base = Path(paths['base']).resolve()
    dest = Path(destination).resolve()
    if dest == base or base in dest.parents:
        raise ValueError('La destination ne peut être dans le dossier de données actives')
    if dest == base.parent and base.name == '.':
        raise ValueError('Destination invalide')
    dest.mkdir(parents=True, exist_ok=True)
    folder = dest / ('StorageScope-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                     + '-' + uuid4().hex[:10])
    folder.mkdir(exist_ok=False)
    try:
        files = backup_databases(paths, folder)
        if not files:
            raise ValueError('Aucune donnée à sauvegarder')
        manifest = {'format': 'storagescope-backup-v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
                    'author': 'Abdelhalim Talbi', 'files': []}
        for file in files:
            size, digest = _hash_file_streaming(Path(file))
            manifest['files'].append({'name': Path(file).name, 'bytes': size,
                                      'sha256': digest})
        (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        if not verify_backup_snapshot(folder):
            raise ValueError('Vérification de sauvegarde échouée')
        return folder, files
    except Exception:
        shutil.rmtree(folder)
        raise


def _hash_file_streaming(path, chunk_size=1024 * 1024):
    """Bounded-memory hashing for multi-gigabyte SQLite snapshots."""
    digest = hashlib.sha256()
    total = 0
    with open(path, 'rb') as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest()


def verify_backup_snapshot(folder):
    """Verify snapshot inventory and hashes; never modify user data."""
    folder = Path(folder)
    try:
        manifest_path = folder / 'manifest.json'
        if manifest_path.is_symlink() or manifest_path.stat().st_size > 2 * 1024 * 1024:
            return False
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        entries = manifest['files']
        if manifest.get('format') != 'storagescope-backup-v1' or not entries:
            return False
        names = [item['name'] for item in entries]
        if len(set(names)) != len(names):
            return False
        # Reject symlinks and nested entries: a snapshot must contain regular local files only.
        if any(p.is_symlink() or not p.is_file() for p in folder.iterdir()):
            return False
        if set(names) != {p.name for p in folder.iterdir() if p.name != 'manifest.json'}:
            return False
        for item in entries:
            name = item['name']
            if (not isinstance(name, str) or not name or name in ('.', '..')
                    or '/' in name or '\\' in name or ':' in name or Path(name).name != name):
                return False
            file = folder / name
            if file.is_symlink() or not file.is_file():
                return False
            if type(item['bytes']) is not int or item['bytes'] < 0 or not isinstance(item['sha256'], str):
                return False
            if file.stat().st_size != item['bytes']:
                return False
            size, digest = _hash_file_streaming(file)
            if size != item['bytes'] or digest != item['sha256']:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def launch():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    from decision_governance_v537 import GovernanceStore
    from decision_workspace_ui_v543 import open_workspace
    from campaign_history_v526 import CampaignHistory

    from windows_preferences_v566 import DEFAULTS, load_preferences, save_preferences
    paths = application_paths()
    try:
        preferences = load_preferences(paths['preferences'])
    except (OSError, ValueError) as exc:
        preferences = dict(DEFAULTS)
        startup_warning = f'Préférences ignorées : {exc}'
    else:
        startup_warning = None
    root = tk.Tk()
    root.title(f'StorageScope {VERSION} — Console Windows')
    root.geometry(preferences['geometry'])
    root.minsize(920, 580)
    # Adapt typography and spacing to Windows scaling; keep user font preferences.
    from windows_accessibility_v617 import display_metrics
    ui_metrics = display_metrics(root.winfo_screenwidth(), root.winfo_screenheight(),
                                 max(0.5, min(4.0, root.winfo_fpixels('1i') / 96.0)))
    root.option_add('*Font', 'Segoe UI 10')
    style = ttk.Style(root)
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    elif 'clam' in style.theme_names():
        style.theme_use('clam')
    style.configure('Nav.TButton', font=('Segoe UI', 11), padding=(14, 12), anchor='w')
    style.configure('Hero.TLabel', font=('Segoe UI', 25, 'bold'), foreground='#172a43')
    style.configure('Subtle.TLabel', foreground='#53657c')
    style.configure('Section.TLabel', font=('Segoe UI', 11, 'bold'), foreground='#31547b')
    style.configure('Selected.Nav.TButton', font=('Segoe UI', 11, 'bold'), padding=(14, 12), anchor='w')
    style.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'))
    style.configure('Heading.TLabel', font=('Segoe UI', 13, 'bold'))
    style.configure('Metric.TLabel', font=('Segoe UI', 16, 'bold'))
    root.configure(background='#e9eff5')
    style.configure('Treeview', rowheight=ui_metrics['rowheight'], font=('Segoe UI', 10))
    style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
    style.configure('TNotebook.Tab', padding=(16, 9))
    status = tk.StringVar(value=startup_warning or 'Prêt · Mode local · Aucune action automatique en production')
    search_text = tk.StringVar()
    search_bar = ttk.Frame(root, padding=(18, 7))
    search_bar.pack(side='top', fill='x')
    ttk.Label(search_bar, text='Aller à un espace :').pack(side='left', padx=(0, 8))
    search_entry = ttk.Entry(search_bar, textvariable=search_text, width=38)
    search_entry.pack(side='left', fill='x', expand=True)
    # Keyboard hint is available in the help menu; omit on compact screens.
    def focus_global_search():
        search_entry.focus_set()
        search_entry.selection_range(0, 'end')
    def search_destination():
        value = search_text.get().strip().casefold()
        if not value:
            focus_global_search()
            return
        from windows_navigation_v569 import route
        destination = route(value)
        if destination:
            navigate_safely(destination)
            return
        status.set('Aucun espace trouvé · essayez Décisions, Campagnes, Diagnostic ou Sauvegardes')
    search_entry.bind('<Return>', lambda event: search_destination())
    ttk.Button(search_bar, text='Ouvrir', command=search_destination).pack(side='left')
    main = ttk.Frame(root)
    main.pack(fill='both', expand=True)
    sidebar = ttk.Frame(main, padding=15)
    sidebar.pack(side='left', fill='y')
    ttk.Label(sidebar, text='STORAGESCOPE', style='Heading.TLabel').pack(anchor='w', pady=(10, 3))
    ttk.Label(sidebar, text='Architecture & gouvernance', style='Subtle.TLabel').pack(anchor='w', pady=(0, 20))
    ttk.Separator(sidebar).pack(fill='x', pady=(0, 12))
    ttk.Label(sidebar, text='ESPACES DE TRAVAIL', style='Section.TLabel').pack(anchor='w', pady=(0, 8))
    content = ttk.Frame(main, padding=ui_metrics['content_padding'])
    content.pack(side='left', fill='both', expand=True)
    pages = {}
    current = {'page': None}
    navigation_buttons = {}

    from windows_page_controller_v590 import PageController
    controller = PageController(('Accueil', 'Gouvernance', 'Campagnes', 'Diagnostic', 'Maintenance'))
    def show_page(name):
        def render(page):
            previous = current['page']
            if previous == page:
                return
            previous_styles = {label: button.cget('style') for label, button in navigation_buttons.items()}
            previous_status = status.get()
            previous_preference = preferences.get('last_page')
            try:
                pages[page].pack(fill='both', expand=True)
                if previous is not None:
                    pages[previous].pack_forget()
                for label, button in navigation_buttons.items():
                    button.configure(style='Selected.Nav.TButton' if label == page else 'Nav.TButton')
                status.set(f'{page} · StorageScope {VERSION}')
                preferences['last_page'] = page
                current['page'] = page
            except Exception:
                # Restore both visual and logical state, not only the frames.
                for label, button in navigation_buttons.items():
                    try:
                        button.configure(style=previous_styles[label])
                    except Exception:
                        pass
                try:
                    pages[page].pack_forget()
                    if previous is not None:
                        pages[previous].pack(fill='both', expand=True)
                finally:
                    status.set(previous_status)
                    if previous_preference is None:
                        preferences.pop('last_page', None)
                    else:
                        preferences['last_page'] = previous_preference
                    current['page'] = previous
                raise
        controller.navigate(name, render)

    def navigate_safely(name):
        """Single error boundary for sidebar, search, shortcuts and home cards."""
        try:
            show_page(name)
            return True
        except Exception as exc:
            # The controller retains the previous page on initialization errors.
            status.set(f'{name} · ouverture impossible : {type(exc).__name__}: {exc}')
            messagebox.showerror('Ouverture de ' + name, str(exc), parent=root)
            return False

    pending_governance_filter = {'value': None}
    governance_refresh = {'callback': None}
    def open_governance(*, deadline=None):
        if deadline is not None and deadline not in ('overdue', 'due_today'):
            raise ValueError('unsupported dashboard deadline')
        if deadline is not None:
            pending_governance_filter['value'] = {'deadline': deadline}
        opened = navigate_safely('Gouvernance')
        if opened and deadline is not None and governance_refresh['callback'] is not None:
            governance_refresh['callback']({'deadline': deadline})
        return opened

    def open_benchmarks():
        return navigate_safely('Campagnes')

    def run_backup():
        folder = filedialog.askdirectory(parent=root, title='Choisir un dossier de sauvegarde distinct')
        if not folder:
            return
        try:
            snapshot, files = backup_snapshot(paths, folder)
            messagebox.showinfo('Sauvegarde vérifiée', f'{len(files)} fichier(s) sauvegardé(s) sans écrasement.\n{snapshot}', parent=root)
        except (OSError, sqlite3.Error, ValueError) as exc:
            messagebox.showerror('Sauvegarde', str(exc), parent=root)

    def home():
        from windows_home_v570 import home_cards, health_summary
        page = ttk.Frame(content)
        ttk.Label(page, text='Votre espace de pilotage', style='Hero.TLabel').pack(anchor='w', pady=(5, 6))
        ttk.Label(page, text='Un point d’entrée pour vos décisions, campagnes et contrôles locaux.',
                  foreground='#566579').pack(anchor='w', pady=(0, 20))
        heading = ttk.Frame(page)
        heading.pack(fill='x', pady=(0, 12))
        ttk.Label(heading, text='État de votre espace', style='Heading.TLabel').pack(side='left')
        health_label = ttk.Label(heading, text='')
        health_label.pack(side='right')
        def update_health():
            states = {}
            for key in ('decisions', 'campaigns'):
                try:
                    states[key] = database_health(paths[key])
                except (OSError, sqlite3.Error) as exc:
                    states[key] = f'ERREUR: {exc}'
            health_label.configure(text=health_summary(states))
        # Read-only overview: no database creation, no automatic production action.
        from windows_dashboard_v602 import dashboard_summary, metric_label
        summary_row = ttk.Frame(page)
        summary_row.pack(fill='x', pady=(0, 12))
        metric_widgets = {}
        for key, label in (('decisions', 'Décisions actives'), ('overdue', 'En retard'),
                           ('due_today', 'À traiter aujourd’hui'), ('campaigns', 'Campagnes')):
            tile = ttk.Frame(summary_row, padding=(10, 8), relief='groove', borderwidth=1)
            tile.pack(side='left', fill='x', expand=True, padx=(0, 6))
            ttk.Label(tile, text=label, style='Subtle.TLabel').pack(anchor='w')
            value_label = ttk.Label(tile, text='—', style='Metric.TLabel')
            value_label.pack(anchor='w')
            metric_widgets[key] = value_label
            if key == 'due_today':
                ttk.Button(tile, text='Voir les échéances du jour →', command=lambda: open_governance(deadline='due_today')).pack(anchor='w')
            elif key == 'overdue':
                ttk.Button(tile, text='Voir les retards →', command=lambda: open_governance(deadline='overdue')).pack(anchor='w')
            elif key == 'decisions':
                ttk.Button(tile, text='Voir les décisions →', command=open_governance).pack(anchor='w')
            elif key == 'campaigns':
                ttk.Button(tile, text='Voir les campagnes →', command=open_benchmarks).pack(anchor='w')
        def refresh_overview():
            snapshot = dashboard_summary(paths)
            for key, widget in metric_widgets.items():
                source = 'campaigns' if key == 'campaigns' else 'decisions'
                widget.configure(text=metric_label(snapshot[key],
                    missing=snapshot['empty'].get(source, False),
                    error=source in snapshot['errors']))
            update_health()
        ttk.Button(page, text='Actualiser les indicateurs', command=refresh_overview).pack(anchor='e', pady=(0, 8))
        refresh_overview()
        ttk.Separator(page).pack(fill='x', pady=(0, 14))
        ttk.Label(page, text='Actions courantes', style='Heading.TLabel').pack(anchor='w', pady=(0, 10))
        actions = {'Gouvernance': open_governance, 'Campagnes': open_benchmarks,
                   'Diagnostic': lambda: navigate_safely('Diagnostic'),
                   'Maintenance': lambda: navigate_safely('Maintenance')}
        for card in home_cards():
            if card['group'] == 'support' and not getattr(page, '_support_heading_added', False):
                ttk.Label(page, text='Contrôles et maintenance', style='Heading.TLabel').pack(anchor='w', pady=(18, 8))
                page._support_heading_added = True
            line = ttk.Frame(page, padding=(12, 9), relief='groove', borderwidth=1)
            line.pack(fill='x', pady=4)
            body = ttk.Frame(line)
            body.pack(side='left', fill='x', expand=True)
            ttk.Label(body, text=card['title'], style='Heading.TLabel').pack(anchor='w')
            ttk.Label(body, text=card['description'], foreground='#566579',
                      wraplength=570).pack(anchor='w', pady=(3, 0))
            ttk.Button(line, text=card['action'] + '  →', command=actions[card['page']]).pack(side='right', padx=(14, 0))
        ttk.Label(page, text='Ctrl+1 Accueil  ·  Ctrl+2 Gouvernance  ·  Ctrl+3 Campagnes  ·  Ctrl+F Navigation',
                  foreground='#566579').pack(anchor='w', pady=(18, 0))
        ttk.Label(page, text='Mode local : aucune action automatique sur les équipements de production.',
                  foreground='#566579').pack(anchor='w', pady=(8, 0))
        return page

    def diagnostics():
        page = ttk.Frame(content)
        ttk.Label(page, text='Diagnostic local', style='Title.TLabel').pack(anchor='w', pady=(5, 18))
        results = tk.Text(page, height=15, wrap='word', font=('Consolas', 10), state='disabled')
        results.pack(fill='both', expand=True)
        def refresh():
            lines = [f'StorageScope {VERSION}', f'Python : {sys.version.split()[0]}',
                     f'Plateforme : {sys.platform}', f'Données : {paths["base"]}', '']
            for key in ('decisions', 'campaigns'):
                try:
                    state = database_health(paths[key])
                except (OSError, sqlite3.Error) as exc:
                    state = f'ERREUR: {exc}'
                lines.append(f'{key} : {state}')
            results.configure(state='normal')
            results.delete('1.0', 'end')
            results.insert('1.0', '\n'.join(lines))
            results.configure(state='disabled')
        ttk.Button(page, text='Actualiser le diagnostic', command=refresh).pack(anchor='w', pady=12)
        def review_storage_topology():
            chosen = filedialog.askopenfilename(
                parent=root, title='Choisir un inventaire SAN/NAS JSON (lecture seule)',
                filetypes=[('Topologie JSON', '*.json'), ('Tous les fichiers', '*.*')])
            if not chosen:
                return
            try:
                report = assess_topology_file(chosen)
                rendered = format_risk_report(report)
            except (OSError, ValueError) as exc:
                status.set('SAN/NAS · fichier non analysé')
                messagebox.showerror('Analyse SAN/NAS', str(exc), parent=root)
                return
            results.configure(state='normal')
            results.delete('1.0', 'end')
            results.insert('1.0', rendered)
            results.configure(state='disabled')
            status.set(f"SAN/NAS · {report['assessment']} · {report['finding_count']} constat(s)")
        ttk.Button(page, text='Analyser une topologie SAN/NAS (JSON)…',
                   command=review_storage_topology).pack(anchor='w', pady=(0, 12))
        ttk.Label(page, text='Analyse locale en lecture seule · Aucun accès aux équipements ou à la CMDB',
                  style='Subtle.TLabel').pack(anchor='w')
        def review_cmdb_snapshot():
            chosen = filedialog.askopenfilename(
                parent=root, title='Choisir un inventaire CMDB JSON (lecture seule)',
                filetypes=[('Inventaire JSON', '*.json'), ('Tous les fichiers', '*.*')])
            if not chosen:
                return
            try:
                report = review_cmdb_file(chosen)
                rendered = format_cmdb_report(report)
            except (OSError, ValueError) as exc:
                status.set('CMDB · fichier non analysé')
                messagebox.showerror('Réconciliation CMDB', str(exc), parent=root)
                return
            results.configure(state='normal')
            results.delete('1.0', 'end')
            results.insert('1.0', rendered)
            results.configure(state='disabled')
            status.set(f"CMDB · {report['assessment']} · {report['candidate_count']} candidat(s)")
        ttk.Button(page, text='Réconcilier un inventaire CMDB (JSON)…',
                   command=review_cmdb_snapshot).pack(anchor='w', pady=(0, 12))
        ttk.Label(page, text='Revue humaine · Provenance et conflits conservés · Aucune fusion automatique',
                  style='Subtle.TLabel').pack(anchor='w')
        def review_vendor_snapshot():
            chosen = filedialog.askopenfilename(
                parent=root, title='Importer un snapshot fournisseur NAS (JSON, lecture seule)',
                filetypes=[('Snapshot JSON', '*.json'), ('Tous les fichiers', '*.*')])
            if not chosen:
                return
            try:
                from vendor_snapshot_import_v6201 import load_snapshot_with_digest, normalize
                snapshot, digest = load_snapshot_with_digest(chosen)
                report = normalize(snapshot, source_sha256=digest)
                topology = report['topology']
                lines = [
                    'Inventaire NAS fournisseur — observation hors ligne',
                    f"Fournisseur : {report['vendor']}",
                    f"Source : {report['source_ref']}",
                    f"SHA-256 du fichier source : {report['snapshot_sha256']}",
                    f"Collecté le : {report['collected_at']}",
                    f"Évaluation : {report['assessment']}",
                    f"Systèmes retenus : {len(topology['assets'])}",
                    f"Partages retenus : {len(topology['shares'])}",
                    f"Enregistrements rejetés : {len(report['rejected'])}",
                    f"Identités système en quarantaine : {len(report['quarantined_system_ids'])}",
                    f"NAS avec partages en quarantaine : {len(report['quarantined_share_asset_ids'])}",
                    'Aucune modification de la CMDB ou des équipements.',
                ]
                if report['rejected']:
                    lines += ['', 'Rejets (20 premiers) :'] + report['rejected'][:20]
                if report['quarantined_system_ids']:
                    lines += ['', 'Systèmes en quarantaine (20 premiers) :'] + report['quarantined_system_ids'][:20]
                if report['quarantined_share_asset_ids']:
                    lines += ['', 'NAS dont les partages sont en quarantaine (20 premiers) :'] + report['quarantined_share_asset_ids'][:20]
                rendered = '\n'.join(lines)
            except (OSError, ValueError, TypeError) as exc:
                status.set('Snapshot NAS · import refusé')
                messagebox.showerror('Import fournisseur NAS', str(exc), parent=root)
                return
            results.configure(state='normal')
            results.delete('1.0', 'end')
            results.insert('1.0', rendered)
            results.configure(state='disabled')
            status.set(f"Snapshot NAS · {report['assessment']} · {len(topology['assets'])} système(s)")
        ttk.Button(page, text='Importer un inventaire NetApp / PowerScale / FlashBlade (JSON)…',
                   command=review_vendor_snapshot).pack(anchor='w', pady=(0, 12))
        refresh()
        return page

    def settings():
        page = ttk.Frame(content)
        ttk.Label(page, text='Données et maintenance', style='Title.TLabel').pack(anchor='w', pady=(5, 18))
        ttk.Label(page, text=f'Dossier local : {paths["base"]}', wraplength=650).pack(anchor='w', pady=(0, 20))
        ttk.Button(page, text='Sauvegarder les bases SQLite et les vues', command=run_backup).pack(anchor='w', pady=8)
        ttk.Label(page, text='Sauvegarde horodatée dans un nouveau dossier, avec empreintes SHA-256 vérifiées.\nAucun écrasement ni restauration automatique.', wraplength=650).pack(anchor='w', pady=12)
        return page

    pages['Accueil'] = home()
    governance_page = ttk.Frame(content)
    campaigns_page = ttk.Frame(content)
    pages['Gouvernance'] = governance_page
    pages['Campagnes'] = campaigns_page

    def open_inventory_review():
        from governance_desktop import launch as launch_inventory_review
        launch_inventory_review(parent=root)

    def initialize_governance():
        review_toolbar = ttk.Frame(governance_page, padding=(6, 6))
        review_toolbar.pack(side='top', fill='x')
        ttk.Button(review_toolbar, text='Réconciliation des inventaires / revue humaine…',
                   command=open_inventory_review).pack(side='left')
        store = GovernanceStore(paths['decisions'])
        pending = pending_governance_filter['value']
        open_workspace(governance_page, store, str(paths['views']), embedded=True, initial_filters=pending, on_filter_ready=lambda callback: governance_refresh.update(callback=callback))
        pending_governance_filter['value'] = None

    def initialize_campaigns():
        from campaign_dashboard_v527 import launch_dashboard
        launch_dashboard(paths['campaigns'], parent=campaigns_page)

    controller.register('Gouvernance', initialize_governance,
                        lambda: (governance_refresh.update(callback=None), [child.destroy() for child in governance_page.winfo_children()]))
    controller.register('Campagnes', initialize_campaigns,
                        lambda: [child.destroy() for child in campaigns_page.winfo_children()])

    pages['Diagnostic'] = diagnostics()
    pages['Maintenance'] = settings()
    for name in ('Accueil', 'Gouvernance', 'Campagnes', 'Diagnostic', 'Maintenance'):
        action = open_governance if name == 'Gouvernance' else open_benchmarks if name == 'Campagnes' else lambda n=name: navigate_safely(n)
        button = ttk.Button(sidebar, text=name, style='Nav.TButton', command=action)
        button.pack(fill='x', pady=4)
        navigation_buttons[name] = button
    ttk.Separator(sidebar).pack(fill='x', pady=20)
    ttk.Label(sidebar, text='AIDE ET RACCOURCIS', style='Section.TLabel').pack(anchor='w')
    ttk.Label(sidebar, text='Ctrl+F  Rechercher\nCtrl+1  Accueil\nCtrl+2  Gouvernance\nCtrl+3  Campagnes\nF5  Diagnostic', style='Subtle.TLabel', justify='left').pack(anchor='w', pady=(8, 18))
    ttk.Label(sidebar, text='Abdelhalim Talbi · v'+VERSION, style='Subtle.TLabel').pack(anchor='w')
    menu = tk.Menu(root)
    filemenu = tk.Menu(menu, tearoff=False)
    filemenu.add_command(label='Accueil', command=lambda: navigate_safely('Accueil'))
    filemenu.add_command(label='Sauvegarder les données…', command=run_backup)
    filemenu.add_separator()
    filemenu.add_command(label='Quitter', command=root.destroy)
    menu.add_cascade(label='Fichier', menu=filemenu)
    toolsmenu = tk.Menu(menu, tearoff=False)
    toolsmenu.add_command(label='Gouvernance', command=open_governance)
    toolsmenu.add_command(label='Réconciliation des inventaires…', command=open_inventory_review)
    toolsmenu.add_command(label='Campagnes', command=open_benchmarks)
    toolsmenu.add_command(label='Diagnostic', command=lambda: navigate_safely('Diagnostic'))
    menu.add_cascade(label='Outils', menu=toolsmenu)
    helpmenu = tk.Menu(menu, tearoff=False)
    helpmenu.add_command(label='À propos', command=lambda: messagebox.showinfo('À propos', f'StorageScope {VERSION}\nAuteur : Abdelhalim Talbi\nApplication locale, aucune activation automatique en production.', parent=root))
    menu.add_cascade(label='Aide', menu=helpmenu)
    root.config(menu=menu)
    def close_application():
        preferences['geometry'] = f'{root.winfo_width()}x{root.winfo_height()}'
        try:
            save_preferences(paths['preferences'], preferences)
        except (OSError, ValueError) as exc:
            if not messagebox.askyesno('Préférences', f'Enregistrement impossible : {exc}\nQuitter quand même ?', parent=root):
                return
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', close_application)
    filemenu.entryconfigure('Quitter', command=close_application)
    from windows_context_menu_v567 import attach_text_context_menu
    attach_text_context_menu(search_entry, root)
    # Context menu is attached by the reusable Windows text menu helper.
    root.bind('<Escape>', lambda event: navigate_safely('Accueil') if root.focus_get() != search_entry else search_entry.delete(0, 'end'))
    root.bind('<Control-1>' , lambda event: navigate_safely('Accueil'))
    root.bind('<Control-2>', lambda event: open_governance())
    root.bind('<Control-3>', lambda event: open_benchmarks())
    root.bind('<F5>', lambda event: navigate_safely('Diagnostic'))
    root.bind('<Control-f>', lambda event: focus_global_search())
    root.bind('<Control-F>', lambda event: focus_global_search())
    root.bind('<Control-s>', lambda event: run_backup())
    root.bind('<Alt-Left>', lambda event: navigate_safely('Accueil'))

    ttk.Label(root, textvariable=status, padding=(18, 10)).pack(side='bottom', fill='x')
    try:
        show_page(preferences['last_page'])
    except Exception as exc:
        show_page('Accueil')
        status.set(f'Ouverture de l’espace impossible : {exc}')
        root.after_idle(lambda: messagebox.showwarning('Ouverture de l’espace', str(exc), parent=root))
    root.mainloop()


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ['--version']:
        print(VERSION)
        return 0
    if len(args) == 2 and args[0] == '--version-file':
        from pathlib import Path
        Path(args[1]).write_text(VERSION + '\n', encoding='utf-8')
        return 0
    if args == ['--self-test']:
        # The frozen smoke test must not create a persistent user-data folder:
        # Inno Setup treats an existing data folder as an upgrade and requires
        # a verified backup. Use an isolated temporary directory instead.
        from tempfile import TemporaryDirectory
        from windows_release_check_v567 import runtime_self_test
        with TemporaryDirectory(prefix='storagescope-selftest-') as temporary:
            return runtime_self_test(application_paths(temporary))
    if len(args) == 2 and args[0] == '--storage-replay-audit':
        from storage_replay_ledger_v6222 import inspect_ledger
        print(json.dumps(inspect_ledger(args[1]), sort_keys=True))
        return 0
    if len(args) == 2 and args[0] == '--storage-replay-init':
        from storage_replay_ledger_v6222 import initialize_ledger
        print(json.dumps(initialize_ledger(args[1]), sort_keys=True))
        return 0
    if len(args) == 3 and args[0] == '--storage-replay-register':
        from storage_replay_ledger_v6222 import register_snapshot
        from storage_risk_desktop_v6196 import load_topology_file
        print(json.dumps(register_snapshot(load_topology_file(args[1]), args[2]),
                         sort_keys=True))
        return 0
    if len(args) == 3 and args[0] == '--storage-risk-file':
        # Frozen Windows CLI evidence: explicit input and a new, non-overwriting report.
        export_risk_report(args[1], args[2])
        return 0
    if len(args) == 3 and args[0] == '--cmdb-review-file':
        # Frozen Windows CLI: local provenance-aware review, never overwrite evidence.
        export_cmdb_report(args[1], args[2])
        return 0
    if len(args) == 3 and args[0] == '--vendor-snapshot-file':
        # Offline vendor import: frozen Windows CLI, strictly read-only input,
        # exclusive output, no live array access or CMDB writes.
        from vendor_snapshot_import_v6201 import main as vendor_snapshot_main
        return vendor_snapshot_main(args[1:])
    if args and args[0] == '--benchmarks':
        if len(args) != 2:
            raise SystemExit('Usage: --benchmarks DATABASE')
        from campaign_dashboard_v527 import launch_dashboard
        launch_dashboard(args[1])
        return
    if args:
        raise SystemExit('Unknown arguments: ' + ' '.join(args))
    launch()


if __name__ == '__main__':
    try:
        code = main()
        if isinstance(code, int):
            sys.exit(code)
    except Exception as exc:
        print(f'StorageScope startup failed: {exc}', file=sys.stderr)
        sys.exit(1)
