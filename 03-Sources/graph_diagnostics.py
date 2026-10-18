"""Bounded non-blocking graph diagnostics; author Abdelhalim Talbi."""
from graph_layout import route_interference

def diagnose_routes(routes, center, cancel_check=None, max_routes=250):
    """Sample a deterministic prefix; never claim a full-graph count if sampled."""
    if type(max_routes) is not int or max_routes < 1: raise ValueError('max_routes')
    if cancel_check and cancel_check():
        from route_scheduler import RouteCancelled
        raise RouteCancelled()
    subset=tuple(routes[:max_routes])
    # Bound cost by sampling; graph-wide quadratic diagnostic is deliberately avoided.
    value=route_interference(subset) if subset else (0,0)
    if cancel_check and cancel_check():
        from route_scheduler import RouteCancelled
        raise RouteCancelled()
    return {'interference':value,'sampled':len(subset),'total':len(routes),'complete':len(subset)==len(routes)}
