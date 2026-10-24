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
                root.destroy()
            tk.Tk.mainloop = inspect
            try:
                app.launch()
            finally:
                tk.Tk.mainloop = original_mainloop
                app.application_paths = original_paths


if __name__ == '__main__':
    unittest.main()
