"""Deterministic graph layout for StorageScope. Author: Abdelhalim Talbi."""
from math import ceil
from collections import OrderedDict

def layout_nodes(nodes, width=850, columns=3, horizontal_gap=24, vertical_gap=32):
    """Return positions with a fixed lane grid and non-overlapping 190x48 cards."""
    if not isinstance(width,(int,float)) or width < 300: raise ValueError('Invalid width')
    if not isinstance(columns,int) or isinstance(columns,bool) or columns < 1: raise ValueError('Invalid columns')
    columns=min(columns,5)
    card_width=190
    cell=max(card_width+horizontal_gap, width/columns)
    actual_width=max(width,columns*cell)
    output=[]
    for i,node in enumerate(nodes):
        x=(i%columns+0.5)*cell
        y=140+(i//columns)*(48+vertical_gap)
        output.append((node,x,y))
    return output, actual_width, 210+max(0,ceil(len(nodes)/columns)-1)*(48+vertical_gap)

def filter_nodes(nodes, kinds=None, query=''):
    """Case-insensitive filter preserving stable order."""
    if kinds is not None: kinds=set(kinds)
    needle=query.strip().casefold()
    return [node for node in nodes if (kinds is None or node[0] in kinds) and
            (not needle or needle in ' '.join(map(str,node[:3])).casefold())]


GRAPH_KINDS = ('RÉSERVE', 'ADR', 'ACTION', 'PREUVE', 'DOCUMENT')

def grouped_nodes(nodes, collapsed=(), limit=60):
    """Stable grouping, optional collapse, and bounded progressive rendering.

    Returns (visible_nodes, groups, remaining). No data is discarded: a
    collapsed group is summarized and a limited page can be expanded.
    """
    if isinstance(limit,bool) or not isinstance(limit,int) or limit<1 or limit>10000:
        raise ValueError('Invalid graph limit')
    collapsed=set(collapsed)
    groups={}
    for node in nodes:
        groups.setdefault(node[0],[]).append(node)
    order=[k for k in GRAPH_KINDS if k in groups]+sorted(k for k in groups if k not in GRAPH_KINDS)
    visible=[]
    for kind in order:
        group=groups[kind]
        if kind in collapsed:
            visible.append(('GROUPE',kind,f'{len(group)} élément(s)',any(n[3] for n in group)))
        else:
            visible.extend(group)
    remaining=max(0,len(visible)-limit)
    return visible[:limit],[(kind,len(groups[kind])) for kind in order],remaining


def layout_grouped(nodes, width=850, columns=3):
    """Place nodes in separate type bands, with no card overlap."""
    if not isinstance(width,(int,float)) or width<300:raise ValueError('Invalid width')
    if isinstance(columns,bool) or not isinstance(columns,int) or columns<1:raise ValueError('Invalid columns')
    columns=min(columns,5)
    lane=max(214,width/columns);actual=max(width,columns*lane)
    output=[];y=140;current=None;index=0
    for node in nodes:
        group=node[1] if node[0]=='GROUPE' else node[0]
        if group!=current:
            if current is not None:y+=max(1,(index+columns-1)//columns)*80+42
            current=group;index=0
        x=(index%columns+.5)*lane
        yy=y+(index//columns)*80
        output.append((node,x,yy));index+=1
    return output,actual,max(230,max((yy for _,_,yy in output),default=140)+90)


def orthogonal_routes(positions, root_x, root_bottom=68, branch_y=96):
    """Stable Manhattan paths: common vertical stem, short horizontal bus, vertical drops.

    Paths terminate at the top of each card; connectors are drawn before cards.
    """
    if not isinstance(root_x,(int,float)) or not isinstance(branch_y,(int,float)):
        raise ValueError('Invalid graph coordinates')
    if branch_y <= root_bottom: raise ValueError('Branch must be below root')
    routes=[]
    for node,x,y in positions:
        if y-24 <= branch_y: raise ValueError('Node overlaps connector bus')
        routes.append([(root_x,root_bottom),(root_x,branch_y),(x,branch_y),(x,y-24)])
    return routes

def minimap_geometry(content_width,content_height,view_width,view_height,map_width=180,map_height=115,scroll_x=0,scroll_y=0):
    """Return scaled content dimensions and clamped viewport box in mini-map pixels."""
    if min(content_width,content_height,view_width,view_height,map_width,map_height)<=0:
        raise ValueError('Dimensions must be positive')
    scale=min(map_width/content_width,map_height/content_height)
    w,h=content_width*scale,content_height*scale
    x=max(0,min(w,scroll_x*scale));y=max(0,min(h,scroll_y*scale))
    return (w,h,(x,y,min(w,x+view_width*scale),min(h,y+view_height*scale)))


def routed_connections(positions, root_x, root_bottom=68, bus_y=96, lane_gap=5):
    """Separated orthogonal fan-out, with independent horizontal tracks.

    Tracks remain above the first card. The deterministic ordering prevents
    connectors from running through any card in the grouped layout.
    """
    if not isinstance(root_x,(int,float)) or not isinstance(bus_y,(int,float)):
        raise ValueError('Invalid routing coordinates')
    if lane_gap<=0 or bus_y<=root_bottom:raise ValueError('Invalid routing geometry')
    if not positions:return []
    first_top=min(y-24 for _,_,y in positions)
    if first_top<=bus_y:raise ValueError('Cards overlap routing corridor')
    ordered=sorted(enumerate(positions),key=lambda t:(abs(t[1][1]-root_x),t[1][1],t[0]))
    n=len(positions)
    available=first_top-bus_y
    gap=min(lane_gap,available/(n+1))
    paths=[None]*n
    for rank,(index,(_,x,y)) in enumerate(ordered):
        track=bus_y+(rank+1)*gap
        # Individual trunk offset separates parallel paths near the root.
        paths[index]=[(root_x,root_bottom),(root_x,track),(x,track),(x,y-24)]
    return paths


def minimap_scroll_fraction(click, map_extent, content_extent, viewport_extent):
    """Convert minimap click into a clamped Tk canvas scroll fraction."""
    if min(map_extent,content_extent,viewport_extent)<=0:raise ValueError('Invalid minimap dimensions')
    if content_extent<=viewport_extent:return 0.0
    target=(max(0,min(map_extent,click))/map_extent)*content_extent-viewport_extent/2
    return max(0.0,min(1.0,target/content_extent))


def route_obstacles(paths, rectangles, clearance=0):
    """Return (route index, rectangle index) for interior segment/card intersections.

    A shared endpoint on a card boundary is allowed. This is a diagnostic,
    not a claim that arbitrary Manhattan routing is collision-free.
    """
    if clearance < 0: raise ValueError('Negative clearance')
    conflicts=[]
    for pi,path in enumerate(paths):
        for ri,(left,top,right,bottom) in enumerate(rectangles):
            if left>=right or top>=bottom:raise ValueError('Invalid rectangle')
            a,b,c,d=left-clearance,top-clearance,right+clearance,bottom+clearance
            for (x1,y1),(x2,y2) in zip(path,path[1:]):
                if x1==x2 and a<x1<c and max(y1,y2)>b and min(y1,y2)<d:
                    conflicts.append((pi,ri));break
                if y1==y2 and b<y1<d and max(x1,x2)>a and min(x1,x2)<c:
                    conflicts.append((pi,ri));break
    return conflicts


def minimap_viewport(content_width,content_height,view_width,view_height,scroll_x=0,scroll_y=0,map_width=180,map_height=115):
    """Viewport box clamped without shrinking near the right/bottom edges."""
    w,h,_=minimap_geometry(content_width,content_height,view_width,view_height,map_width,map_height)
    bw=min(w,view_width*w/content_width);bh=min(h,view_height*h/content_height)
    x=max(0,min(w-bw,scroll_x*w/content_width));y=max(0,min(h-bh,scroll_y*h/content_height))
    return w,h,(x,y,x+bw,y+bh)


def obstacle_aware_routes(positions, root_x, root_bottom=68, bus_y=96, card_half_width=95, card_half_height=24, clearance=7):
    """Route via inter-column side channels, avoiding other rectangular cards.

    Returns paths in input order. For tightly packed/irregular layouts where no
    collision-free side channel exists, falls back to the old route and reports
    collisions through route_obstacles; never silently asserts perfect routing.
    """
    if clearance <= 0 or card_half_width <= 0 or card_half_height <= 0:
        raise ValueError('Invalid routing clearance/card size')
    base = routed_connections(positions, root_x, root_bottom, bus_y)
    rectangles = [(x-card_half_width,y-card_half_height,x+card_half_width,y+card_half_height)
                  for _,x,y in positions]
    routed=[]
    for i, ((_,x,y), original) in enumerate(zip(positions,base)):
        track=original[1][1]
        end_y=y-card_half_height
        # Prefer right-hand side channel, then left. Each route stays outside
        # earlier cards in the same column before approaching its destination.
        candidates=[]
        for side in (1,-1):
            sx=x+side*(card_half_width+clearance)
            path=[(root_x,root_bottom),(root_x,track),(sx,track),
                  (sx,end_y-clearance),(x,end_y-clearance),(x,end_y)]
            collisions=[j for _,j in route_obstacles([path],rectangles) if j!=i]
            candidates.append((len(collisions),0 if side==1 else 1,path))
        _,_,best=min(candidates,key=lambda item:(item[0],item[1]))
        routed.append(best)
    return routed


def route_interference(paths):
    """Count pairwise interior orthogonal crossings and positive-length overlaps.

    Shared points at segment endpoints are not counted as crossings.
    Returns (crossings, overlaps); overlap counts segment pairs, not pixels.
    """
    crossings=overlaps=0
    for i,a in enumerate(paths):
        for b in paths[i+1:]:
            for p,q in zip(a,a[1:]):
                for r,s in zip(b,b[1:]):
                    ax,ay=p;bx,by=q;cx,cy=r;dx,dy=s
                    if ax==bx and cx==dx and ax==cx and max(min(ay,by),min(cy,dy))<min(max(ay,by),max(cy,dy)):
                        overlaps+=1
                    elif ay==by and cy==dy and ay==cy and max(min(ax,bx),min(cx,dx))<min(max(ax,bx),max(cx,dx)):
                        overlaps+=1
                    elif ax==bx and cy==dy and min(cx,dx)<ax<max(cx,dx) and min(ay,by)<cy<max(ay,by):
                        crossings+=1
                    elif ay==by and cx==dx and min(ax,bx)<cx<max(ax,bx) and min(cy,dy)<ay<max(cy,dy):
                        crossings+=1
    return crossings,overlaps


def optimized_obstacle_routes(positions, root_x, root_bottom=68, bus_y=96, card_half_width=95, card_half_height=24, clearance=7):
    """Greedy deterministic fan-out balancing card collisions and route interference.

    Uses fixed candidate channels and bounded work per edge. Existing route
    endpoints remain unchanged; crossings can remain for dense graphs.
    """
    if clearance<=0 or card_half_width<=0 or card_half_height<=0:
        raise ValueError('Invalid geometry')
    if not positions:return []
    baseline=routed_connections(positions,root_x,root_bottom,bus_y)
    rects=[(x-card_half_width,y-card_half_height,x+card_half_width,y+card_half_height) for _,x,y in positions]
    result=[]
    for i,((_,x,y),base) in enumerate(zip(positions,baseline)):
        track=base[1][1];end=y-card_half_height
        candidates=[]
        for side in (1,-1):
            for extra in (0,clearance*2,clearance*4):
                sx=x+side*(card_half_width+clearance+extra)
                path=[(root_x,root_bottom),(root_x,track),(sx,track),(sx,end-clearance),(x,end-clearance),(x,end)]
                collisions=sum(j!=i for _,j in route_obstacles([path],rects))
                cross,overlap=route_interference(result+[path])
                distance=sum(abs(a-b)+abs(c-d) for (a,c),(b,d) in zip(path,path[1:]))
                candidates.append(((collisions*100000+cross*100+overlap*10+distance*.001),path))
        result.append(min(candidates,key=lambda t:t[0])[1])
    return result


def incremental_route_interference(previous, candidate):
    """Score only pairs involving candidate; prior/prior costs are invariant."""
    return route_interference(list(previous) + [candidate]) if not previous else _candidate_interference(previous, candidate)


def _candidate_interference(previous, candidate):
    crossings = overlaps = 0
    for other in previous:
        for (ax, ay), (bx, by) in zip(candidate, candidate[1:]):
            for (cx, cy), (dx, dy) in zip(other, other[1:]):
                if ax == bx and cx == dx and ax == cx and max(min(ay, by), min(cy, dy)) < min(max(ay, by), max(cy, dy)):
                    overlaps += 1
                elif ay == by and cy == dy and ay == cy and max(min(ax, bx), min(cx, dx)) < min(max(ax, bx), max(cx, dx)):
                    overlaps += 1
                elif ax == bx and cy == dy and min(cx, dx) < ax < max(cx, dx) and min(ay, by) < cy < max(ay, by):
                    crossings += 1
                elif ay == by and cx == dx and min(ax, bx) < cx < max(ax, bx) and min(cy, dy) < ay < max(cy, dy):
                    crossings += 1
    return crossings, overlaps


def _fast_route_hits_rect(path, rect):
    """Equivalent to route_obstacles([path],[rect]) for zero clearance."""
    a,b,c,d=rect
    for (x1,y1),(x2,y2) in zip(path,path[1:]):
        if x1==x2 and a<x1<c and max(y1,y2)>b and min(y1,y2)<d:
            return True
        if y1==y2 and b<y1<d and max(x1,x2)>a and min(x1,x2)<c:
            return True
    return False


def _candidate_may_touch_rect(path, rect):
    """Cheap conservative AABB prefilter; never rejects a true segment collision."""
    xs = [point[0] for point in path]
    ys = [point[1] for point in path]
    left, top, right, bottom = rect
    return min(xs) < right and max(xs) > left and min(ys) < bottom and max(ys) > top


def _route_segments(path):
    """Pre-normalize orthogonal segments once per accepted route."""
    vertical, horizontal = [], []
    for (x1,y1),(x2,y2) in zip(path,path[1:]):
        if x1 == x2:
            vertical.append((x1,min(y1,y2),max(y1,y2)))
        elif y1 == y2:
            horizontal.append((y1,min(x1,x2),max(x1,x2)))
    return vertical, horizontal


def _indexed_interference(recent_segments, candidate):
    """Same strict crossing/overlap semantics as _fast_interference."""
    cv,ch = _route_segments(candidate)
    cross=overlap=0
    for ov,oh in recent_segments:
        for x,a,b in cv:
            for xx,c,d in ov:
                if x==xx and max(a,c)<min(b,d): overlap+=1
            for yy,c,d in oh:
                if c<x<d and a<yy<b: cross+=1
        for y,a,b in ch:
            for yy,c,d in oh:
                if y==yy and max(a,c)<min(b,d): overlap+=1
            for xx,c,d in ov:
                if a<xx<b and c<y<d: cross+=1
    return cross,overlap


class RecentSegmentIndex:
    """Immutable per-card index of bounded recent routes, preserving pair counts."""
    def __init__(self, recent_segments):
        from bisect import bisect_left
        self.vertical = {}
        self.horizontal = {}
        for vertical, horizontal in recent_segments:
            for x, lo, hi in vertical:
                self.vertical.setdefault(x, []).append((lo, hi))
            for y, lo, hi in horizontal:
                self.horizontal.setdefault(y, []).append((lo, hi))
        self.xs = sorted(self.vertical)
        self.ys = sorted(self.horizontal)

    def append(self, segments):
        """Add one accepted route without rebuilding the whole index."""
        from bisect import insort
        vertical, horizontal = segments
        for x, lo, hi in vertical:
            if x not in self.vertical:
                self.vertical[x] = []
                insort(self.xs, x)
            self.vertical[x].append((lo, hi))
        for y, lo, hi in horizontal:
            if y not in self.horizontal:
                self.horizontal[y] = []
                insort(self.ys, y)
            self.horizontal[y].append((lo, hi))

    def discard(self, segments):
        """Remove the oldest route, preserving duplicate segment counts."""
        from bisect import bisect_left
        vertical, horizontal = segments
        for x, lo, hi in vertical:
            values = self.vertical[x]
            values.remove((lo, hi))
            if not values:
                del self.vertical[x]
                self.xs.pop(bisect_left(self.xs, x))
        for y, lo, hi in horizontal:
            values = self.horizontal[y]
            values.remove((lo, hi))
            if not values:
                del self.horizontal[y]
                self.ys.pop(bisect_left(self.ys, y))

    def score(self, candidate):
        from bisect import bisect_right, bisect_left
        cv, ch = _route_segments(candidate)
        crossings = overlaps = 0
        for x, lo, hi in cv:
            overlaps += sum(max(lo,a)<min(hi,b) for a,b in self.vertical.get(x, ()))
            for y in self.ys[bisect_right(self.ys,lo):bisect_left(self.ys,hi)]:
                crossings += sum(a<x<b for a,b in self.horizontal[y])
        for y, lo, hi in ch:
            overlaps += sum(max(lo,a)<min(hi,b) for a,b in self.horizontal.get(y, ()))
            for x in self.xs[bisect_right(self.xs,lo):bisect_left(self.xs,hi)]:
                crossings += sum(a<y<b for a,b in self.vertical[x])
        return crossings, overlaps


def _fast_interference(recent, candidate):
    """Compatibility wrapper retaining the previous scoring semantics."""
    return _indexed_interference([_route_segments(p) for p in recent],candidate)

class ObstacleBucketIndex:
    """X-bucket rectangle index; query only boxes intersecting segment interiors.

    Rectangle IDs are returned in ascending order.  Wide query spans use a
    linear fallback to avoid allocating enormous temporary bucket ranges.
    """
    def __init__(self, rectangles, bucket_width=192):
        from math import floor
        if bucket_width <= 0:
            raise ValueError('bucket_width must be positive')
        self.rectangles = tuple(rectangles)
        self.width = bucket_width
        self.buckets = {}
        for i, (left, top, right, bottom) in enumerate(self.rectangles):
            if right <= left or bottom <= top:
                continue
            first, last = floor(left / bucket_width), floor(right / bucket_width)
            if last - first > 4096:
                self.buckets.setdefault(None, []).append(i)
            else:
                for key in range(first, last + 1):
                    self.buckets.setdefault(key, []).append(i)

    def query(self, path, segment_cache=None):
        """Exact collision IDs, including oversized rectangles and long paths.

        Each rectangle is checked at most once per path. An overflow rectangle
        must still intersect the path; its presence in the overflow list alone
        is not a collision.
        """
        from math import floor
        hits = set()
        overflow = self.buckets.get(None, ())
        for (x1, y1), (x2, y2) in zip(path, path[1:]):
            key = ((x1,y1),(x2,y2)) if (x1,y1) <= (x2,y2) else ((x2,y2),(x1,y1))
            if segment_cache is not None and key in segment_cache:
                hits.update(segment_cache[key])
                if isinstance(segment_cache, OrderedDict):
                    segment_cache.move_to_end(key)
                continue
            segment_hits = set()
            if x1 != x2 and y1 != y2:
                continue
            left, right = sorted((x1, x2))
            first, last = floor(left / self.width), floor(right / self.width)
            if last - first > 4096:
                candidates = range(len(self.rectangles))
            else:
                from itertools import chain
                candidates = chain(overflow, (i for key in range(first, last + 1)
                                               for i in self.buckets.get(key, ())))
            for i in candidates:
                if i in segment_hits:
                    continue
                a,b,c,d = self.rectangles[i]
                if x1 == x2 and a < x1 < c and max(y1,y2) > b and min(y1,y2) < d:
                    segment_hits.add(i)
                elif y1 == y2 and b < y1 < d and max(x1,x2) > a and min(x1,x2) < c:
                    segment_hits.add(i)
            hits.update(segment_hits)
            if segment_cache is not None:
                if len(segment_cache) >= 2048:
                    if isinstance(segment_cache, OrderedDict):
                        segment_cache.popitem(last=False)
                    else:
                        segment_cache.clear()
                segment_cache[key] = frozenset(segment_hits)
        return hits


def scalable_obstacle_routes(positions, root_x, root_bottom=68, bus_y=96,
                             card_half_width=95, card_half_height=24,
                             clearance=7, recent_routes=24, cancel_check=None, _prefix=(), _reuse=None, _old_paths=None, _stats=None):
    """Bounded-work deterministic router for large graphs.

    Spatial x-buckets reduce obstacle candidates; interference is evaluated
    against the most recent `recent_routes` edges. This trades global
    optimality for predictable resource consumption, and never claims zero
    crossings. The shared root stem is intentionally not penalized.
    """
    if clearance <= 0 or card_half_width <= 0 or card_half_height <= 0:
        raise ValueError('Invalid geometry')
    if isinstance(recent_routes, bool) or not isinstance(recent_routes, int) or not 0 <= recent_routes <= 256:
        raise ValueError('Invalid recent route limit')
    if not positions:
        return []
    baseline = routed_connections(positions, root_x, root_bottom, bus_y)
    rectangles = [(x-card_half_width, y-card_half_height, x+card_half_width, y+card_half_height)
                  for _, x, y in positions]
    obstacle_index = ObstacleBucketIndex(rectangles, max(64, 2*card_half_width + clearance))

    result = [list(path) for path in _prefix]
    reused_count = 0
    obstacle_segment_cache = OrderedDict()
    from collections import deque
    recent_segments = deque()
    segment_index = RecentSegmentIndex(()) if recent_routes else None
    from route_scheduler import RouteCancelled
    for prior in result[-recent_routes:] if recent_routes else ():
        accepted = _route_segments(prior)
        recent_segments.append(accepted)
        segment_index.append(accepted)
    for i, ((_, x, y), base) in enumerate(zip(positions, baseline)):
        if i < len(_prefix):
            continue
        if (_reuse is not None and i in _reuse and
            (not recent_routes or (_old_paths is not None and
             result[max(0, i-recent_routes):i] ==
             [list(path) for path in _old_paths[max(0, i-recent_routes):i]]))):
            if cancel_check is not None and cancel_check():
                raise RouteCancelled()
            path = list(_reuse[i])
            reused_count += 1
            result.append(path)
            if recent_routes:
                accepted = _route_segments(path)
                recent_segments.append(accepted)
                segment_index.append(accepted)
                if len(recent_segments) > recent_routes:
                    segment_index.discard(recent_segments.popleft())
            continue
        if cancel_check is not None and cancel_check():
            raise RouteCancelled()
        track = base[1][1]
        end = y-card_half_height
        best = None
        for side in (1, -1):
            for extra in (0, clearance*2, clearance*4):
                if cancel_check is not None and cancel_check():
                    raise RouteCancelled()
                sx = x+side*(card_half_width+clearance+extra)
                path = [(root_x,root_bottom),(root_x,track),(sx,track),
                        (sx,end-clearance),(x,end-clearance),(x,end)]
                collisions = 0
                for j in obstacle_index.query(path, obstacle_segment_cache):
                    if j != i:
                        collisions += 1
                cross, overlap = segment_index.score(path) if segment_index is not None else (0,0)
                distance = sum(abs(a-b)+abs(c-d) for (a,c),(b,d) in zip(path,path[1:]))
                score = collisions*100000+cross*100+overlap*10+distance*.001
                if best is None or score < best[0]:
                    best = (score,path)
        result.append(best[1])
        if recent_routes:
            accepted = _route_segments(best[1])
            recent_segments.append(accepted)
            segment_index.append(accepted)
            if len(recent_segments)>recent_routes:
                segment_index.discard(recent_segments.popleft())
    if _stats is not None:
        _stats.update(prefix_reused=len(_prefix), suffix_reused=reused_count, recomputed=len(result)-len(_prefix)-reused_count)
    return result


class RoutingResultCache:
    """Bounded, immutable snapshots of completed deterministic routing results.

    A changed coordinate, obstacle, option or node identity is a cache miss.
    Cancellations are always checked, including on cache hits. Failed runs
    are never cached. This is an opt-in companion, not an implicit global cache.
    """
    def __init__(self, capacity=4):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError('Invalid cache capacity')
        self.capacity = capacity
        self._entries = OrderedDict()
        self.hits = 0
        self.misses = 0

    def clear(self):
        self._entries.clear()

    def route(self, positions, root_x, root_bottom=68, bus_y=96,
              card_half_width=95, card_half_height=24, clearance=7,
              recent_routes=24, cancel_check=None):
        from route_scheduler import RouteCancelled
        from time import perf_counter
        if cancel_check is not None and cancel_check():
            raise RouteCancelled()
        # Tuple-of-tuples also avoids retaining mutable caller-owned data.
        frozen = tuple((tuple(node) if isinstance(node, list) else node, x, y)
                       for node, x, y in positions)
        key = (frozen, root_x, root_bottom, bus_y, card_half_width,
               card_half_height, clearance, recent_routes)
        try:
            hash(key)
        except TypeError as exc:
            raise ValueError('Unhashable graph node identity') from exc
        if key in self._entries:
            self.hits += 1
            self._entries.move_to_end(key)
            return [list(path) for path in self._entries[key]]
        self.misses += 1
        paths = scalable_obstacle_routes(frozen, root_x, root_bottom, bus_y,
                                        card_half_width, card_half_height,
                                        clearance, recent_routes, cancel_check)
        if cancel_check is not None and cancel_check():
            raise RouteCancelled()
        self._entries[key] = tuple(tuple(point for point in path) for path in paths)
        if len(self._entries) > self.capacity:
            self._entries.popitem(last=False)
        return [list(path) for path in self._entries[key]]


class GeometryRoutingCache(RoutingResultCache):
    """Opt-in cache for metadata-only graph edits (same ordered x/y positions).

    Routing uses node identities neither for track ordering nor collision scores.
    The original RoutingResultCache remains available with strict identity keys.
    Coordinate, order, option or node-count changes always trigger a full run.
    """
    def route(self, positions, root_x, root_bottom=68, bus_y=96,
              card_half_width=95, card_half_height=24, clearance=7,
              recent_routes=24, cancel_check=None):
        from route_scheduler import RouteCancelled
        if cancel_check is not None and cancel_check():
            raise RouteCancelled()
        # No identity is retained: callers can edit labels/status/metadata safely.
        geometry = tuple((x, y) for _, x, y in positions)
        key = (geometry, root_x, root_bottom, bus_y, card_half_width,
               card_half_height, clearance, recent_routes)
        try:
            hash(key)
        except TypeError as exc:
            raise ValueError('Unhashable graph geometry') from exc
        if key in self._entries:
            self.hits += 1
            self._entries.move_to_end(key)
            return [list(path) for path in self._entries[key]]
        self.misses += 1
        # Use lightweight positional identities, so caller-owned metadata is
        # never inspected or retained by the routing engine.
        canonical = tuple((i, x, y) for i, (x, y) in enumerate(geometry))
        from time import perf_counter
        stats = {}
        paths = scalable_obstacle_routes(canonical, root_x, root_bottom, bus_y,
                                        card_half_width, card_half_height,
                                        clearance, recent_routes, cancel_check)
        if cancel_check is not None and cancel_check():
            raise RouteCancelled()
        self._entries[key] = tuple(tuple(path) for path in paths)
        if len(self._entries) > self.capacity:
            self._entries.popitem(last=False)
        return [list(path) for path in self._entries[key]]


class PartialGeometryRoutingCache(GeometryRoutingCache):
    """Conservative suffix reuse, only if every earlier candidate is unaffected.

    A global lane layout change forces a full recalculation. No unverified
    reuse is performed; node identities and metadata are ignored.
    """
    def __init__(self, capacity=4):
        super().__init__(capacity)
        self.partial_reuses = 0
        self.suffix_reuses = 0
        self.validation_skips = 0
        self.validation_checks = 0
        self.validation_budget = 12000
        self.validation_time_seconds = 0.0
        self.validation_attempts = 0
        self.validation_last_seconds = 0.0
        self.validation_last_estimate = 0
        self.validation_delta_rectangles = 0
        self.last_routing_stats = {"prefix_reused": 0, "suffix_reused": 0, "recomputed": 0}
        self.reuse_history = {}  # workload -> recent actual reuse counts
        self.profitability_skips = 0
        self.profitability_probes = 0
        self.profitability_probe_interval = 5
        self._profitability_skip_streak = {}
        self._probe_intervals = {}  # per-workload adaptive interval, bounded 2..16
        self.probe_successes = 0
        self.probe_failures = 0
        # Timing diagnostics are observations, never permission to bypass safety.
        self.routing_time_seconds = 0.0
        self.routing_attempts = 0
        self.last_route_seconds = 0.0
        self.last_validation_fraction = 0.0
        self.workload_timing = {}  # (size, edit count, recent window) -> bounded samples
        self.cost_gate_skips = 0
        self.cost_gate_min_samples = 3
        self.cost_gate_ratio = 1.5
        self.cost_gate_min_validation_seconds = 0.001  # ignore sub-millisecond noise
        self.cost_gate_probe_interval = 5
        self._cost_gate_streak = {}
        self.cost_gate_probes = 0
        self.cost_gate_reactivations = 0
        self.last_cost_gate_decision = "not_applicable"
        self.high_edit_fallbacks = 0
        self.high_edit_threshold = 8
        self.high_edit_ratio_threshold = 0.20
        self.high_edit_min_edits = 8
        self.high_edit_cost_observations = 3
        self.high_edit_adaptive_decisions = 0

    def _should_full_route_for_edits(self, edit_count, graph_size, recent_routes):
        """Conservative cost-aware fallback; never authorizes path reuse.

        Historical measurements only strengthen the decision when enough
        actual samples exist; the legacy eight-edit limit remains a ceiling.
        """
        if edit_count >= self.high_edit_threshold:
            return True
        if graph_size <= 0 or edit_count < self.high_edit_min_edits:
            return False
        if edit_count / graph_size < self.high_edit_ratio_threshold:
            return False
        from statistics import median
        key = (min(8, graph_size // 100), min(8, edit_count), recent_routes)
        samples = self.workload_timing.get(key, ())
        measured = [sample for sample in samples
                    if sample.get('validation_seconds', 0) >= self.cost_gate_min_validation_seconds
                    and sample.get('routing_seconds', 0) > 0]
        if len(measured) < self.high_edit_cost_observations:
            return False
        recent = measured[-self.high_edit_cost_observations:]
        if (median(x['validation_seconds'] for x in recent) >
                self.cost_gate_ratio * median(x['routing_seconds'] for x in recent)
                and all(x.get('reused', 0) == 0 for x in recent)):
            self.high_edit_adaptive_decisions += 1
            return True
        return False

    def calibrate_validation_budget(self, target_seconds=0.025, minimum=1000, maximum=24000):
        """Bound the estimated-work budget using observed validation throughput.

        No observations means retain the existing budget. Calibration never
        bypasses exact routing checks and only changes fallback frequency.
        """
        import math
        if (not math.isfinite(target_seconds) or target_seconds <= 0 or
            isinstance(minimum, bool) or isinstance(maximum, bool) or
            not isinstance(minimum, int) or not isinstance(maximum, int) or
            minimum < 1 or maximum < minimum):
            raise ValueError('Invalid calibration limits')
        if not self.validation_attempts or self.validation_time_seconds <= 0:
            return self.validation_budget
        throughput = self.validation_checks / self.validation_time_seconds
        estimate = int(throughput * target_seconds)
        self.validation_budget = max(minimum, min(maximum, estimate))
        return self.validation_budget

    def route(self, positions, root_x, root_bottom=68, bus_y=96,
              card_half_width=95, card_half_height=24, clearance=7,
              recent_routes=24, cancel_check=None):
        from route_scheduler import RouteCancelled
        from time import perf_counter
        if cancel_check is not None and cancel_check():
            raise RouteCancelled()
        geometry = tuple((x, y) for _, x, y in positions)
        opts = (root_x, root_bottom, bus_y, card_half_width,
                card_half_height, clearance, recent_routes)
        key = (geometry,) + opts
        try:
            hash(key)
        except TypeError as exc:
            raise ValueError('Unhashable graph geometry') from exc
        if key in self._entries:
            self.hits += 1
            self._entries.move_to_end(key)
            return [list(path) for path in self._entries[key]]
        self.misses += 1
        canonical = tuple((i, x, y) for i, (x, y) in enumerate(geometry))
        prefix = ()
        reuse = {}
        validation_attempts_before = self.validation_attempts
        probed_workload = None
        cost_probed_workload = None
        self.last_cost_gate_decision = "not_applicable"
        # Validation is deliberately conservative: all six choices of each
        # reusable edge must be unaffected by old/new changed obstacles.
        if clearance > 0 and card_half_width > 0 and card_half_height > 0 and isinstance(recent_routes, int) and not isinstance(recent_routes, bool) and 0 <= recent_routes <= 256:
            try:
                # Early high-edit decision avoids building a baseline solely
                # to reject partial validation. Preserve other eligible cache
                # candidates, including differing graph lengths.
                candidates = [(k, v) for k, v in reversed(self._entries.items())
                              if k[1:] == opts]
                if candidates and all(
                    len(k[0]) == len(geometry) and
                    self._should_full_route_for_edits(
                        sum(a != b for a, b in zip(k[0], geometry)),
                        len(geometry), recent_routes)
                    for k, _ in candidates):
                    self.high_edit_fallbacks += 1
                    candidates = []
                new_baseline = routed_connections(canonical, root_x, root_bottom, bus_y) if candidates else ()
                for old_key, old_paths in candidates:
                    old_geom, *old_opts = old_key
                    if tuple(old_opts) != opts:
                        continue
                    count = 0
                    for a, b in zip(old_geom, geometry):
                        if a != b:
                            break
                        count += 1
                    if not count or count == len(geometry) and count == len(old_geom):
                        continue
                    old_baseline = routed_connections(tuple((i,x,y) for i,(x,y) in enumerate(old_geom)), root_x, root_bottom, bus_y)
                    if any(old_baseline[i][1][1] != new_baseline[i][1][1] for i in range(count)):
                        continue
                    # Equal-length edits: only obstacles whose rectangles actually
                    # changed can alter candidate collision counts. Unchanged
                    # rectangles cancel out, even when edits are far apart.
                    if len(old_geom) == len(geometry):
                        changed_indices = [j for j, (a, b) in enumerate(zip(old_geom, geometry)) if a != b]
                        changed = tuple(old_geom[j] for j in changed_indices) + tuple(geometry[j] for j in changed_indices)
                        estimated_checks = 6 * count * len(changed)
                        estimated_checks += 12 * (len(geometry)-count) * len(changed_indices)
                    else:
                        changed_indices = []
                        changed = old_geom[count:] + geometry[count:]
                        estimated_checks = 6 * count * len(changed)
                    # For heavily edited equal-size graphs, conservative full
                    # recomputation avoids validation overhead and cache churn.
                    # It never accepts unverified reusable paths.
                    if len(old_geom) == len(geometry) and self._should_full_route_for_edits(len(changed_indices), len(geometry), recent_routes):
                        self.high_edit_fallbacks += 1
                        continue
                    # Repeated zero-reuse outcomes: skip expensive validation.
                    # Never skip full routing or the safety checks on reused paths.
                    size_band = min(8, len(geometry) // 100)
                    edit_band = min(8, len(changed_indices)) if len(old_geom) == len(geometry) else 9
                    workload = (size_band, edit_band, recent_routes)
                    # Conservative cost gate: only after repeated, measured,
                    # zero-reuse validations. Skipping validation never reuses
                    # an unverified path; the normal full router still runs.
                    from statistics import median
                    timing = self.workload_timing.get(workload, ())
                    measured = [t for t in timing if t['validation_seconds'] > 0]
                    if len(measured) >= self.cost_gate_min_samples:
                        recent = measured[-self.cost_gate_min_samples:]
                        if (all(t['reused'] == 0 for t in recent) and
                            median(t['validation_seconds'] for t in recent) >= self.cost_gate_min_validation_seconds and
                            median(t['validation_seconds'] for t in recent) >
                            self.cost_gate_ratio * median(t['routing_seconds'] for t in recent)):
                            streak = self._cost_gate_streak.get(workload, 0) + 1
                            if streak < self.cost_gate_probe_interval:
                                self._cost_gate_streak[workload] = streak
                                self.cost_gate_skips += 1
                                self.last_cost_gate_decision = "full_cost_gate"
                                continue
                            self._cost_gate_streak[workload] = 0
                            self.cost_gate_probes += 1
                            cost_probed_workload = workload
                            self.last_cost_gate_decision = "cost_probe"
                        else:
                            self._cost_gate_streak.pop(workload, None)
                            self.last_cost_gate_decision = "eligible"
                    samples = self.reuse_history.get(workload, ())
                    if cost_probed_workload is not None:
                        pass  # Cost probe takes precedence over reuse-history skipping.
                    elif len(samples) >= 3 and sum(samples[-3:]) == 0:
                        streak = self._profitability_skip_streak.get(workload, 0) + 1
                        if streak < self._probe_intervals.get(workload, self.profitability_probe_interval):
                            self._profitability_skip_streak[workload] = streak
                            self.profitability_skips += 1
                            continue
                        # Periodic probe: retry validation after bounded skips.
                        # The geometric and recent-window checks remain mandatory.
                        self._profitability_skip_streak[workload] = 0
                        self.profitability_probes += 1
                        probed_workload = workload
                    else:
                        self._profitability_skip_streak.pop(workload, None)
                    if estimated_checks > self.validation_budget:
                        self.validation_skips += 1
                        continue
                    from time import perf_counter
                    validation_started = perf_counter()
                    self.validation_checks += estimated_checks
                    self.validation_delta_rectangles = len(changed)
                    self.validation_last_estimate = estimated_checks
                    rectangles = [(x-card_half_width,y-card_half_height,x+card_half_width,y+card_half_height) for x,y in changed]
                    safe = True
                    for i, (x,y) in enumerate(geometry[:count]):
                        track = new_baseline[i][1][1]
                        end = y-card_half_height
                        for side in (1,-1):
                            for extra in (0,clearance*2,clearance*4):
                                sx = x+side*(card_half_width+clearance+extra)
                                path = [(root_x,root_bottom),(root_x,track),(sx,track),(sx,end-clearance),(x,end-clearance),(x,end)]
                                if any(_candidate_may_touch_rect(path, rect) and _fast_route_hits_rect(path, rect) for rect in rectangles):
                                    safe = False
                                    break
                            if not safe: break
                        if not safe: break
                    if safe:
                        prefix = old_paths[:count]
                        # Candidate geometry must be stable. With interference enabled,
                        # the router also verifies the exact preceding recent-route
                        # window before accepting each reused edge.
                        if len(old_geom) == len(geometry):
                            old_rects = [(old_geom[j][0]-card_half_width,old_geom[j][1]-card_half_height,
                                          old_geom[j][0]+card_half_width,old_geom[j][1]+card_half_height) for j in changed_indices]
                            new_rects = [(geometry[j][0]-card_half_width,geometry[j][1]-card_half_height,
                                          geometry[j][0]+card_half_width,geometry[j][1]+card_half_height) for j in changed_indices]
                            for j in range(count, len(geometry)):
                                if old_geom[j] != geometry[j] or old_baseline[j][1][1] != new_baseline[j][1][1]:
                                    continue
                                x, y = geometry[j]
                                track = new_baseline[j][1][1]
                                end = y-card_half_height
                                candidate_safe = True
                                for side in (1,-1):
                                    for extra in (0,clearance*2,clearance*4):
                                        sx = x+side*(card_half_width+clearance+extra)
                                        candidate = [(root_x,root_bottom),(root_x,track),(sx,track),
                                                     (sx,end-clearance),(x,end-clearance),(x,end)]
                                        # Ignore the changed node's own rectangle: it
                                        # is excluded from collision scoring.
                                        for k, idx in enumerate(changed_indices):
                                            if idx != j and ((_candidate_may_touch_rect(candidate, old_rects[k]) and _fast_route_hits_rect(candidate, old_rects[k])) or
                                                             (_candidate_may_touch_rect(candidate, new_rects[k]) and _fast_route_hits_rect(candidate, new_rects[k]))):
                                                candidate_safe = False
                                                break
                                        if not candidate_safe: break
                                    if not candidate_safe: break
                                if candidate_safe:
                                    reuse[j] = old_paths[j]
                        elapsed = perf_counter() - validation_started
                        self.validation_last_seconds = elapsed
                        self.validation_time_seconds += elapsed
                        self.validation_attempts += 1
                        break
                    elapsed = perf_counter() - validation_started
                    self.validation_last_seconds = elapsed
                    self.validation_time_seconds += elapsed
                    self.validation_attempts += 1
            except (ValueError, TypeError, IndexError):
                prefix = ()
        routing_started = perf_counter()
        stats = {}
        paths = scalable_obstacle_routes(canonical, root_x, root_bottom, bus_y,
                                        card_half_width, card_half_height,
                                        clearance, recent_routes, cancel_check,
                                        _prefix=prefix, _reuse=reuse,
                                        _old_paths=old_paths if reuse else None, _stats=stats)
        route_elapsed = perf_counter() - routing_started
        if cancel_check is not None and cancel_check():
            raise RouteCancelled()
        self.routing_time_seconds += route_elapsed
        self.routing_attempts += 1
        self.last_route_seconds = route_elapsed
        self.last_validation_fraction = self.validation_last_seconds / max(1e-12, route_elapsed + self.validation_last_seconds) if self.validation_attempts > validation_attempts_before else 0.0
        if 'workload' in locals():
            samples = self.workload_timing.setdefault(workload, [])
            samples.append({'routing_seconds': route_elapsed,
                            'validation_seconds': self.validation_last_seconds if self.validation_attempts > validation_attempts_before else 0.0,
                            'edits': len(changed_indices),
                            'reused': stats.get('prefix_reused', 0) + stats.get('suffix_reused', 0),
                            'recomputed': stats.get('recomputed', 0)})
            if len(samples) > 12:
                del samples[:-12]
        if prefix:
            self.partial_reuses += 1
        self.suffix_reuses += stats.get("suffix_reused", 0)
        self.last_routing_stats = stats
        if cost_probed_workload is not None:
            if stats.get("prefix_reused", 0) + stats.get("suffix_reused", 0) > 0:
                self.cost_gate_reactivations += 1
                self._cost_gate_streak.pop(cost_probed_workload, None)
                # Remove stale zero-reuse timing evidence so subsequent
                # decisions can collect fresh measurements.
                self.workload_timing[cost_probed_workload] = [
                    sample for sample in self.workload_timing.get(cost_probed_workload, ())
                    if sample['reused'] > 0
                ]
                self.last_cost_gate_decision = "reactivated"
        if probed_workload is not None:
            # Feedback uses actual accepted suffix reuse, not merely candidates.
            # Failed probes become less frequent; successful ones restore the
            # default interval. The conservative full-routing fallback remains.
            if stats.get("suffix_reused", 0) > 0:
                self.probe_successes += 1
                self._probe_intervals[probed_workload] = self.profitability_probe_interval
            else:
                self.probe_failures += 1
                current = self._probe_intervals.get(probed_workload, self.profitability_probe_interval)
                self._probe_intervals[probed_workload] = min(16, max(2, current * 2))
        if prefix and "workload" in locals():
            history = self.reuse_history.setdefault(workload, [])
            history.append(stats.get("suffix_reused", 0))
            if len(history) > 12:
                del history[:-12]
        self._entries[key] = tuple(tuple(path) for path in paths)
        if len(self._entries) > self.capacity:
            self._entries.popitem(last=False)
        return [list(path) for path in self._entries[key]]
