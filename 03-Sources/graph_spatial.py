"""Immutable uniform-grid spatial index for viewport queries. Author: Abdelhalim Talbi."""
from collections import defaultdict
from math import floor

class SpatialIndex:
    def __init__(self, entries, bounds_fn, cell=256):
        if cell <= 0: raise ValueError('cell must be positive')
        self.entries=tuple(entries)
        self.cell=cell
        buckets=defaultdict(list)
        for i,entry in enumerate(self.entries):
            x1,y1,x2,y2=bounds_fn(entry)
            if x2<x1 or y2<y1: raise ValueError('invalid item bounds')
            for gx in range(floor(x1/cell),floor(x2/cell)+1):
                for gy in range(floor(y1/cell),floor(y2/cell)+1):
                    buckets[(gx,gy)].append(i)
        self.buckets=dict(buckets)
        self.bounds=tuple(bounds_fn(e) for e in self.entries)

    def query(self, bounds, zoom=1.0, margin=100):
        if zoom<=0 or margin<0: raise ValueError('invalid viewport')
        left,top,right,bottom=bounds
        if right<left or bottom<top: raise ValueError('invalid viewport bounds')
        x1,y1,x2,y2=(left-margin)/zoom,(top-margin)/zoom,(right+margin)/zoom,(bottom+margin)/zoom
        ids=set()
        for gx in range(floor(x1/self.cell),floor(x2/self.cell)+1):
            for gy in range(floor(y1/self.cell),floor(y2/self.cell)+1):
                ids.update(self.buckets.get((gx,gy),()))
        return [self.entries[i] for i in sorted(ids) if self.bounds[i][2]>=x1 and self.bounds[i][0]<=x2 and self.bounds[i][3]>=y1 and self.bounds[i][1]<=y2]

def card_index(positions, cell=256):
    return SpatialIndex(positions,lambda p:(p[1]-95,p[2]-24,p[1]+95,p[2]+24),cell)

def route_index(routes, cell=256):
    def box(route):
        xs=[p[0] for p in route];ys=[p[1] for p in route]
        return min(xs),min(ys),max(xs),max(ys)
    return SpatialIndex((r for r in routes if r),box,cell)
