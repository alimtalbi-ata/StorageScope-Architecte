"""Native Tkinter Infrastructure smoke test (requires Windows interactive desktop).

This deliberately uses the real application process and OS-level key events.
The workflow must fail if no desktop or UI is available.
"""
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

@unittest.skipUnless(sys.platform == 'win32' and os.environ.get('STORAGESCOPE_GUI_SMOKE') == '1',
                     'Native Windows desktop GUI smoke only')
class WindowsInfrastructureGuiSmoke(unittest.TestCase):
    def test_infrastructure_window_opens_and_navigation_exists(self):
        import ctypes
        import tkinter as tk
        from tkinter import ttk
        sources = Path(__file__).resolve().parents[1] / '03-Sources'
        sys.path.insert(0, str(sources))
        import storagescope_windows as app
        # Replace mainloop with a bounded, deterministic inspection of actual widgets.
        original_mainloop = tk.Tk.mainloop
        original_paths = app.application_paths
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            app.application_paths = lambda root=None: original_paths(folder)
            inspected = []
            def inspect(root):
                root.update_idletasks()
                def walk(widget):
                    yield widget
                    for child in widget.winfo_children():
                        yield from walk(child)
                widgets = list(walk(root))
                labels = [str(w.cget('text')) for w in widgets
                          if isinstance(w, (ttk.Button, ttk.Label))]
                inspected.extend(labels)
                self.assertTrue(any('Infrastructure' == label for label in labels),
                                'Infrastructure navigation button missing')
                self.assertTrue(any('Importer un snapshot' in label for label in labels),
                                'Vendor snapshot import action missing')
                self.assertTrue(any('Exporter le tableau en CSV' in label for label in labels),
                                'Inventory CSV export action missing')
                self.assertTrue(any(isinstance(w, ttk.Treeview) for w in widgets),
                                'Inventory table missing')
                from unittest.mock import patch
                import json
                snapshot = Path(folder) / 'snapshot.json'
                snapshot.write_text(json.dumps({
                    'schema': 'storagescope.vendor-snapshot.v1',
                    'vendor': 'netapp_ontap',
                    'source_ref': 'gui-acceptance',
                    'collected_at': '2026-10-24T10:00:00Z',
                    'systems': [{
                        'serial_number': 'GUI-001', 'cluster_name': 'nas-gui',
                        'capacity_used_bytes': 1073741824,
                        'capacity_total_bytes': 10737418240,
                        'volumes': [{'uuid': 'vol-gui', 'protocol': 'NFS',
                                     'used_bytes': 1073741824,
                                     'quota_bytes': 2147483648}]
                    }]
                }), encoding='utf-8')
                buttons = [w for w in widgets if isinstance(w, ttk.Button)]
                importer = next(w for w in buttons if 'Importer un snapshot' in w.cget('text'))
                exporter = next(w for w in buttons if 'Exporter le tableau' in w.cget('text'))
                table = next(w for w in widgets if isinstance(w, ttk.Treeview))
                with patch('tkinter.filedialog.askopenfilename', return_value=str(snapshot)):
                    importer.invoke()
                self.assertEqual(len(table.get_children()), 1, 'Import button did not populate NAS table')
                table.selection_set(table.get_children()[0])
                table.event_generate('<<TreeviewSelect>>')
                root.update()
                details = [w for w in widgets if isinstance(w, tk.Text)]
                self.assertTrue(details, 'NAS share details widget missing')
                self.assertTrue(any('vol-gui' in w.get('1.0', 'end') for w in details),
                                'Selecting NAS asset did not reveal its share details')
                destination = Path(folder) / 'inventory.csv'
                with patch('tkinter.filedialog.asksaveasfilename', return_value=str(destination)):
                    with patch('tkinter.messagebox.showinfo'):
                        exporter.invoke()
                self.assertTrue(destination.is_file(), 'Export button did not create CSV')
                self.assertIn('GUI-001', destination.read_text(encoding='utf-8-sig'))
                # Invalid import must preserve the last valid inventory (fail closed).
                invalid = Path(folder) / 'invalid-snapshot.json'
                invalid.write_text('{ malformed JSON', encoding='utf-8')
                with patch('tkinter.filedialog.askopenfilename', return_value=str(invalid)):
                    with patch('tkinter.messagebox.showerror') as error_dialog:
                        importer.invoke()
                self.assertTrue(error_dialog.called, 'Invalid import did not surface a GUI error')
                self.assertEqual(len(table.get_children()), 1,
                                 'Invalid import destroyed previously loaded inventory')
                # Existing CSV must never be overwritten, even through the GUI.
                original_csv = destination.read_bytes()
                with patch('tkinter.filedialog.asksaveasfilename', return_value=str(destination)):
                    with patch('tkinter.messagebox.showerror') as overwrite_error:
                        exporter.invoke()
                self.assertTrue(overwrite_error.called, 'Existing CSV overwrite was not rejected')
                self.assertEqual(destination.read_bytes(), original_csv,
                                 'Existing CSV was unexpectedly modified')
                root.destroy()
            tk.Tk.mainloop = inspect
            try:
                app.launch()
            finally:
                tk.Tk.mainloop = original_mainloop
                app.application_paths = original_paths


if __name__ == '__main__':
    unittest.main()
