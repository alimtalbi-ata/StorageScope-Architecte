"""Reusable Tk Entry context menu, without clipboard side effects on import.
Author: Abdelhalim Talbi.
"""
def attach_text_context_menu(entry, root):
    import tkinter as tk
    menu = tk.Menu(entry, tearoff=False)
    menu.add_command(label='Couper', command=lambda: entry.event_generate('<<Cut>>'))
    menu.add_command(label='Copier', command=lambda: entry.event_generate('<<Copy>>'))
    menu.add_command(label='Coller', command=lambda: entry.event_generate('<<Paste>>'))
    menu.add_separator()
    menu.add_command(label='Tout sélectionner', command=lambda: entry.selection_range(0, 'end'))
    menu.add_command(label='Effacer', command=lambda: entry.delete(0, 'end'))
    def popup(event):
        try:
            entry.focus_set()
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    entry.bind('<Button-3>', popup)
    return menu
