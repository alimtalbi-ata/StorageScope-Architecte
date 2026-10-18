"""Real Tkinter Treeview benchmark: full rebuild vs existing adaptive strategy."""
import json, statistics, time, tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import reconcile_tree_rows

def benchmark(n, repeats=5):
    root=tk.Tk(); root.withdraw()
    tree=ttk.Treeview(root,columns=('value',),show='headings');tree.pack()
    base=[(str(i),(f'value-{i}',)) for i in range(n)]
    scenarios={
      'unchanged':base,
      'single_change':[(i,('updated',) if i=='1' else v) for i,v in base],
      'mass_change':[(i,('updated',)) for i,v in base],
      'reverse':list(reversed(base))}
    results={}
    for scenario,rows in scenarios.items():
      timings={}
      for method in ('rebuild','adaptive'):
        samples=[]
        for _ in range(repeats):
          tree.delete(*tree.get_children())
          for iid,v in base:tree.insert('', 'end',iid=iid,values=v)
          tree.selection_set(str(n//2));tree.yview_moveto(.3)
          t=time.perf_counter()
          if method=='rebuild':
            tree.delete(*tree.get_children())
            for iid,v in rows:tree.insert('', 'end',iid=iid,values=v)
          else:reconcile_tree_rows(tree,rows)
          root.update_idletasks()
          samples.append((time.perf_counter()-t)*1000)
          assert tuple(tree.get_children())==tuple(i for i,_ in rows)
          if method=='adaptive':
            assert tree.selection()==(str(n//2),)
        timings[method]=round(statistics.median(samples),3)
      results[scenario]=timings
    root.destroy()
    return {'rows':n,'repeats':repeats,'results':results}
if __name__=='__main__':
    out={'environment':'Linux/Xvfb; real ttk.Treeview; not Windows','runs':[benchmark(n) for n in (100,500,1000)]}
    Path(__file__).with_name('benchmark_treeview_v671_results.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
