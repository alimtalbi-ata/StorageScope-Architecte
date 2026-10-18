"""Real Tkinter Treeview benchmark, requires graphical display or Xvfb."""
import json, statistics, time, tkinter as tk
from tkinter import ttk
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import reconcile_tree_rows

def measure(n=1000, repetitions=5):
 root=tk.Tk();root.withdraw();tree=ttk.Treeview(root,columns=('value',),show='headings');tree.pack()
 base=[(str(i),(f'value-{i}',)) for i in range(n)]
 scenarios={'unchanged':base,'single_change':[(i,('updated',) if i=='1' else v) for i,v in base], 'mass_change':[(i,('updated',)) for i,v in base], 'reverse':list(reversed(base))}
 results={}
 for name,rows in scenarios.items():
  timings={}
  for method in ('rebuild','adaptive'):
   samples=[]
   for _ in range(repetitions):
    for iid in tree.get_children():tree.delete(iid)
    for iid,v in base:tree.insert('', 'end', iid=iid,values=v)
    tree.selection_set(str(n//2));tree.yview_moveto(.3)
    start=time.perf_counter()
    if method=='rebuild':
     for iid in tree.get_children():tree.delete(iid)
     for iid,v in rows:tree.insert('', 'end',iid=iid,values=v)
    else:reconcile_tree_rows(tree,rows)
    root.update_idletasks()
    samples.append((time.perf_counter()-start)*1000)
    assert tuple(tree.get_children())==tuple(i for i,_ in rows)
   timings[method]=round(statistics.median(samples),3)
  results[name]=timings
 root.destroy();return {'rows':n,'repetitions':repetitions,'environment':'Tkinter real Treeview; display-dependent','results':results}
if __name__=='__main__':
 output={'runs':[measure(n) for n in (100,1000)]}
 p=Path(__file__).with_name('benchmark_treeview_v669_results.json');p.write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2))
