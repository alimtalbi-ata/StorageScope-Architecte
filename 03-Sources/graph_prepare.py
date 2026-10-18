"""Thread-confined SQLite read and pure layout. Author: Abdelhalim Talbi."""
import sqlite3
from pathlib import Path
from fast_dashboard import decision_graph
from graph_layout import filter_nodes, grouped_nodes, layout_grouped
from route_scheduler import RouteCancelled

def prepare_graph(request, cancel_check=None):
    """Request contains only immutable primitives; worker owns its SQLite connection."""
    dbpath,did,kind,search,collapsed,page_limit,viewport,*fingerprint=request
    if cancel_check and cancel_check(): raise RouteCancelled()
    uri=Path(dbpath).resolve().as_uri()+'?mode=ro'
    db=sqlite3.connect(uri,uri=True,timeout=3)
    try:
        db.execute('PRAGMA query_only=ON')
        model=decision_graph(db,did)
    finally:
        db.close()
    if cancel_check and cancel_check(): raise RouteCancelled()
    nodes=[('RÉSERVE',r['id'],r['status'],bool(r['blocking']) and r['status']=='OPEN') for r in model['reservations']]
    nodes += [(a['kind'],a['id'],a['state'],a['kind']=='ACTION' and a['state']=='OPEN') for a in model['artifacts']]
    nodes=filter_nodes(nodes,None if kind=='TOUS' else (kind,),search)
    nodes,groups,remaining=grouped_nodes(nodes,set(collapsed),page_limit)
    if cancel_check and cancel_check(): raise RouteCancelled()
    cols=max(1,min(3,int(viewport//230)))
    positions,width,height=layout_grouped(nodes,max(550,viewport),cols)
    return (model['decision']['status'],positions,width,height,len(groups),remaining)
