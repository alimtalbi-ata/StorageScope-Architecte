"""Native Tkinter Infrastructure smoke test (requires Windows interactive desktop).

This creates actual Tkinter widgets and invokes their button callbacks.
Native file pickers are mocked to keep acceptance deterministic.
"""
import os
import sys
import unittest
from pathlib import Path

@unittest.skipUnless(sys.platform == 'win32' and os.environ.get('STORAGESCOPE_GUI_SMOKE') == '1',
                     'Native Windows desktop GUI smoke only')
class WindowsInfrastructureGuiSmoke(unittest.TestCase):
    def test_infrastructure_window_opens_and_navigation_exists(self):
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
                # Empty inventory: export must not create a file or prompt for a destination.
                with patch('tkinter.filedialog.asksaveasfilename') as save_dialog:
                    with patch('tkinter.messagebox.showinfo') as empty_info:
                        exporter.invoke()
                self.assertTrue(empty_info.called, 'Empty inventory warning missing')
                save_dialog.assert_not_called()
                # Canceling the file picker must leave the table untouched.
                with patch('tkinter.filedialog.askopenfilename', return_value=''):
                    importer.invoke()
                self.assertFalse(table.get_children(), 'Canceled import modified inventory')
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
                # Switching vendors must replace, not append, inventory and share details.
                for vendor, serial_key, name_key, used_key, total_key, collection, share_key in (
                    ('dell_powerscale', 'serial', 'cluster', 'used_bytes', 'total_bytes', 'exports', 'id'),
                    ('pure_flashblade', 'array_id', 'name', 'space_used_bytes', 'space_total_bytes', 'shares', 'id'),
                ):
                    vendor_snapshot = Path(folder) / (vendor + '.json')
                    vendor_snapshot.write_text(json.dumps({
                        'schema': 'storagescope.vendor-snapshot.v1',
                        'vendor': vendor, 'source_ref': 'gui-acceptance',
                        'collected_at': '2026-10-24T10:00:00Z',
                        'systems': [{
                            serial_key: 'GUI-002', name_key: 'nas-gui-2',
                            used_key: 1073741824, total_key: 10737418240,
                            collection: [{share_key: 'share-smb', 'protocol': 'SMB',
                                          'used_bytes': 1073741824, 'quota_bytes': 2147483648}]
                        }]
                    }), encoding='utf-8')
                    with patch('tkinter.filedialog.askopenfilename', return_value=str(vendor_snapshot)):
                        importer.invoke()
                    self.assertEqual(len(table.get_children()), 1,
                                     'Switching vendor appended stale inventory rows')
                    row = table.get_children()[0]
                    self.assertEqual(table.item(row, 'values')[2], vendor + ':GUI-002')
                    table.selection_set(row)
                    table.event_generate('<<TreeviewSelect>>')
                    root.update()
                    self.assertTrue(any('share-smb' in w.get('1.0', 'end') for w in details),
                                    'Vendor SMB share details missing after switching vendor')
                    self.assertFalse(any('vol-gui' in w.get('1.0', 'end') for w in details),
                                     'Previous vendor share details leaked into new inventory')
                # Restore NetApp for the existing CSV and fail-closed regression assertions.
                with patch('tkinter.filedialog.askopenfilename', return_value=str(snapshot)):
                    importer.invoke()
                table.selection_set(table.get_children()[0])
                table.event_generate('<<TreeviewSelect>>')
                root.update()
                # Canceling export must not write a file or raise a modal error.
                with patch('tkinter.filedialog.asksaveasfilename', return_value=''):
                    with patch('tkinter.messagebox.showerror') as cancel_error:
                        exporter.invoke()
                cancel_error.assert_not_called()
                self.assertFalse((Path(folder) / 'inventory.csv').exists(),
                                 'Canceled export unexpectedly created a CSV')
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
                self.assertTrue(any('vol-gui' in w.get('1.0', 'end') for w in details),
                                'Invalid import erased previously selected NAS share details')
                self.assertEqual(table.item(table.get_children()[0], 'values')[2],
                                 'netapp_ontap:GUI-001',
                                 'Invalid import changed the previously loaded NAS identity')
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
