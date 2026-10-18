"""Actual Tk Treeview timings; run with xvfb-run on Linux or python on Windows."""
import sys,time,json,statistics,tkinter as tk
from tkinter import ttk
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'03-Sources'))
from governance_desktop import reconcile_tree_rows
def run(n, scenario, method):
 root=tk.Tk();root.withdraw();tree=ttk.Treeview(root,columns=('value',),show='headings')
 old=[(str(i),(str(i),)) for i in range(n)]
 new=old if scenario=='unchanged' else ([(str(i),(str(i)+'x',)) for i in range(n)] if scenario=='updated' else list(reversed(old)))
 reconcile_tree_rows(tree,old);root.update_idletasks()
 start=time.perf_counter()
 if method=='reconcile': reconcile_tree_rows(tree,new)
 else:
  tree.delete(*tree.get_children())
  for iid,values in new:tree.insert('', 'end',iid=iid,values=values)
 root.update_idletasks();elapsed=(time.perf_counter()-start)*1000
 assert list(tree.get_children())==[i for i,_ in new]
 root.destroy();return elapsed
def main():
 result=[]
 for n in (100,1000):
  for scenario in ('unchanged','updated','reversed'):
   for method in ('rebuild','reconcile'):
    samples=[run(n,scenario,method) for _ in range(3)]
    result.append({'rows':n,'scenario':scenario,'method':method,'median_ms':round(statistics.median(samples),3),'samples_ms':[round(x,3) for x in samples]})
 print(json.dumps({'platform':sys.platform,'tk_patchlevel':tk.Tcl().eval('info patchlevel'),'results':result},indent=2))
if __name__=='__main__':main()
