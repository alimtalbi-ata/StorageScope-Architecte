"""Viewport culling helpers for StorageScope graph. Author: Abdelhalim Talbi."""

def visible_cards(positions, bounds, zoom=1.0, margin=100, half_width=95, half_height=24):
    """Return only cards intersecting the expanded viewport; preserve input order."""
    if zoom <= 0 or margin < 0: raise ValueError("invalid viewport parameters")
    left, top, right, bottom = bounds
    if right < left or bottom < top: raise ValueError("invalid viewport bounds")
    x1=(left-margin)/zoom; y1=(top-margin)/zoom
    x2=(right+margin)/zoom; y2=(bottom+margin)/zoom
    return [(node,x,y) for node,x,y in positions if x+half_width>=x1 and x-half_width<=x2 and y+half_height>=y1 and y-half_height<=y2]


def visible_routes(routes, bounds, zoom=1.0, margin=100):
    """Cull connector polylines by their bounding boxes."""
    if zoom <= 0 or margin < 0: raise ValueError("invalid viewport parameters")
    left,top,right,bottom=bounds
    if right < left or bottom < top: raise ValueError("invalid viewport bounds")
    x1=(left-margin)/zoom; y1=(top-margin)/zoom
    x2=(right+margin)/zoom; y2=(bottom+margin)/zoom
    result=[]
    for route in routes:
        if not route: continue
        xs=[p[0] for p in route]; ys=[p[1] for p in route]
        if max(xs)>=x1 and min(xs)<=x2 and max(ys)>=y1 and min(ys)<=y2:
            result.append(route)
    return result
