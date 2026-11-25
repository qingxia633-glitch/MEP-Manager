"""Geometric evidence within a caller-selected WCS window. No label-driven grouping."""
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math

# Absolute tolerance in source WCS units for six-decimal exporter coordinates.
EPS = 0.0001


def stable_id(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True,
                                     allow_nan=False, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class Segment:
    handle: str
    a: tuple
    b: tuple

    @property
    def flat(self):
        return abs(self.a[1]-self.b[1]) <= EPS

    @property
    def y(self):
        return (self.a[1]+self.b[1])/2

    def x_at(self, y):
        x0,y0 = self.a
        x1,y1 = self.b
        return x0 + (x1-x0)*(y-y0)/(y1-y0)

    def spans_y(self, low, high):
        ends=sorted((self.a[1],self.b[1]))
        return ends[0]-EPS <= low <= high <= ends[1]+EPS

    def intersects(self, vertical):
        if not vertical.spans_y(self.y,self.y):
            return False
        left,right=sorted((self.a[0],self.b[0]))
        return left-EPS <= vertical.x_at(self.y) <= right+EPS


def clusters(values):
    groups=[]
    for value, item in sorted(values, key=lambda p:p[0]):
        if not groups or value-groups[-1][0]>EPS:
            groups.append((value, []))
        groups[-1][1].append(item)
    return groups


def extent(obj):
    if 'bounds' in obj:
        return obj['bounds']
    pts=obj.get('points',[])
    if pts:
        xs,ys=zip(*[p[:2] for p in pts])
        return [min(xs),min(ys),max(xs),max(ys)]
    return None


def header_candidates(rows, members):
    terms={'序号','图例','线型','线路名称','线路型号规格及穿管敷设方式',
           '型号及规格','单位','安装方式及安装高度','名称'}
    headers=defaultdict(list)
    for row in rows:
        for cell in row['cells']:
            for h in cell['members']:
                text=members[h].get('decoded_text') or ''
                if ''.join(text.split()) in terms:
                    headers[row['table_id']].append((row,cell,h,text))
    for row in rows:
        for cell in row['cells']:
            for header,head_cell,h,text in headers[row['table_id']]:
                if header['y_interval'][0]<row['y_interval'][0]-EPS:
                    continue
                # Require the same observed rails on both sides. A similar X
                # coordinate elsewhere does not carry a column heading.
                if all(set(cell['boundary'][side]) & set(head_cell['boundary'][side])
                       for side in ('left','right')):
                    row['column_role_candidates'].append(dict(header_text=text,source=h,
                        header_cell_id=head_cell['cell_id'],cell_id=cell['cell_id']))


def overlaps(a,b):
    return a[2]>=b[0]-EPS and b[2]>=a[0]-EPS and a[3]>=b[1]-EPS and b[3]>=a[1]-EPS


def segments(objects):
    horizontal,vertical=[],[]
    for obj in objects:
        if not obj.get('straight'):
            continue
        pts=[tuple(p[:2]) for p in obj['points']]
        for a,b in zip(pts,pts[1:]+(pts[:1] if obj.get('closed') else [])):
            if math.dist(a,b)<=EPS:
                continue
            seg=Segment(obj['handle'],a,b)
            if seg.flat:
                horizontal.append(seg)
            elif abs(a[0]-b[0]) <= abs(a[1]-b[1])*.01:
                # Retain actual sloped rail coordinates at both intersections.
                vertical.append(seg)
    return horizontal,vertical


def grid_components(horiz,vert):
    adjacent=defaultdict(set)
    for h in horiz:
        for v in vert:
            if h.intersects(v):
                adjacent[h].add(v)
                adjacent[v].add(h)
    seen=set()
    for initial in adjacent:
        if initial in seen:
            continue
        stack=[initial]
        part=set()
        while stack:
            seg=stack.pop()
            if seg not in part:
                part.add(seg)
                stack.extend(adjacent[seg]-part)
        seen.update(part)
        yield sorted(part,key=lambda s:(s.handle,s.a,s.b))


def cover(segments, left, right):
    """Return covering intervals and duplicate/overlapping boundary flag."""
    spans=sorted((max(left,min(s.a[0],s.b[0])),min(right,max(s.a[0],s.b[0])),s.handle)
                 for s in segments)
    end=left
    duplicate=False
    handles=set()
    for a,b,h in spans:
        if b-a<=EPS:
            continue
        if a>end+EPS:
            return [],False
        duplicate |= a<end-EPS
        handles.add(h)
        end=max(end,b)
    return (sorted(handles),duplicate) if end>=right-EPS else ([],False)


def cell_bands(part, region, window):
    horizontals=[s for s in part if s.flat]
    verticals=[s for s in part if not s.flat]
    levels=clusters((s.y,s) for s in horizontals)
    # One dangling stroke alone cannot split a whole table into two rows.
    levels=[(y,hs) for y,hs in levels if len(clusters(
        (v.x_at(y),v) for v in verticals if any(h.intersects(v) for h in hs)))>=2]
    for (low,lower),(high,upper) in zip(levels,levels[1:]):
        rails=clusters((v.x_at((low+high)/2),v) for v in verticals if v.spans_y(low,high))
        band=[]
        for (_,ls),(_,rs) in zip(rails,rails[1:]):
            l,r=ls[0],rs[0]
            x0,x1=l.x_at(low),r.x_at(low)
            x2,x3=l.x_at(high),r.x_at(high)
            if min(x1-x0,x3-x2)<=EPS:
                continue
            if (min(x0,x2)<window[0]-EPS or max(x1,x3)>window[2]+EPS or
                low<window[1]-EPS or high>window[3]+EPS):
                continue
            bottom,dup0=cover(lower,x0,x1)
            top,dup1=cover(upper,x2,x3)
            if not bottom and not top:
                continue
            reasons=[]
            if not bottom or not top:
                reasons.append('missing_horizontal_boundary')
            if any(min(x0,x2)+EPS<v.x_at(y)<max(x1,x3)-EPS
                   for y in (low,high) for v in verticals if v.spans_y(y,y) and v not in ls+rs):
                reasons.append('merge_or_missing_divider')
            if any(low+EPS<h.y<high-EPS and
                   (h.intersects(l) or h.intersects(r)) for h in horizontals):
                reasons.append('partial_horizontal_divider')
            duplicate=dup0 or dup1 or len(ls)>1 or len(rs)>1
            if any(abs(v.x_at(y)-ref.x_at(y))>EPS for ref,vs in [(l,ls),(r,rs)]
                   for v in vs for y in (low,high)):
                reasons.append('competing_rail_geometry')
            if duplicate:
                reasons.append('overlapping_boundary_witnesses')
            polygon=[[x0,low],[x1,low],[x3,high],[x2,high]]
            edges={'bottom':bottom,'top':top,'left':sorted({v.handle for v in ls}),
                   'right':sorted({v.handle for v in rs})}
            band.append(dict(cell_id=stable_id(region,polygon,edges),polygon=polygon,boundary=edges,
                             members=[],unresolved_items=reasons,evidence_status=(
                                 'unresolved' if not top or not bottom or any(
                                     'divider' in x or x=='competing_rail_geometry' for x in reasons)
                                 else 'ambiguous' if duplicate else 'bounded')))
        if band:
            yield low,high,band,lower,upper


def outer_evidence(part):
    """Show the observed envelope and its support. Do not fill a side from the window."""
    hs=[s for s in part if s.flat]
    vs=[s for s in part if not s.flat]
    xs=[x for s in hs for x,y in (s.a,s.b)]
    lo=min(s.y for s in hs)
    hi=max(s.y for s in hs)
    left,right=min(xs),max(xs)
    ends={}
    for key,y in [('bottom',lo),('top',hi)]:
        ends[key]=cover([s for s in hs if abs(s.y-y)<=EPS],left,right)[0]
    for key,x in [('left',left),('right',right)]:
        ends[key]=sorted({s.handle for s in vs if s.spans_y(lo,hi) and
                          max(abs(s.x_at(y)-x) for y in (lo,hi))<=EPS})
    return dict(envelope_wcs=[left,lo,right,hi],rectangular_outer_sides=ends,
                rectangular_outer_status='bounded' if all(ends.values()) and hi-lo>EPS else 'unresolved')


def location(bounds, polygon):
    (a,lo),(b,_),(c,hi),(d,_)=polygon
    x,y,xx,yy=bounds
    if not overlaps(bounds,[min(a,d),lo,max(b,c),hi]):
        return 'outside'
    left=lambda v:a+(d-a)*(v-lo)/(hi-lo)
    right=lambda v:b+(c-b)*(v-lo)/(hi-lo)
    y0,y1=max(y,lo),min(yy,hi)
    if xx<min(left(y0),left(y1))-EPS or x>max(right(y0),right(y1))+EPS:
        return 'outside'
    if y>lo+EPS and yy<hi-EPS and x>max(left(y),left(yy))+EPS and xx<min(right(y),right(yy))-EPS:
        return 'inside'
    return 'intersects'


def reconstruct(source, name, window, z, objects):
    if (not name or not all(source.get(k) for k in ('project_id','drawing','snapshot_id'))
        or len(window)!=4 or not all(math.isfinite(v) for v in [*window,z])
        or window[0]>=window[2] or window[1]>=window[3]):
        raise ValueError('invalid source or WCS window')
    window=list(map(float,window))
    z=float(z)
    region=stable_id('legend-region/1',source,name,window,z)
    objects=sorted(objects,key=lambda o:o['handle'])
    if len({o['handle'] for o in objects})!=len(objects):
        raise ValueError('duplicate top-level identity')
    for obj in objects:
        if 'identity' in obj:
            identity=obj['identity']
            if (identity.get('project_id')!=source['project_id'] or identity.get('drawing_ref')!=source['drawing']
                or identity.get('snapshot_id')!=source['snapshot_id'] or identity.get('parent_path')!=[]
                or identity.get('handle')!=obj['handle']):
                raise ValueError('foreign object identity')
    members={o['handle']:o for o in objects}
    horiz,vert=segments(objects)
    rows=[]
    tables=[]
    boundary_handles=set()
    issues=[]
    for part in grid_components(horiz,vert):
        table_id=stable_id(region,[(s.handle,s.a,s.b) for s in part])
        tables.append(dict(table_id=table_id,**outer_evidence(part)))
        for low,high,cells,lower,upper in cell_bands(part,region,window):
            sides=[c['boundary'] for c in cells]
            rid=stable_id(region,low,high,sides)
            for edge in sides:
                for handles in edge.values():
                    boundary_handles.update(handles)
            rows.append(dict(row_id=rid,legend_region_id=region,table_id=table_id,row_boundary=sides,
                             horizontal_spans={key:sorted((min(s.a[0],s.b[0]),max(s.a[0],s.b[0]),s.handle)
                                for s in ss) for key,ss in [('bottom',lower),('top',upper)]},
                             y_interval=[low,high],row_only_candidates=[],
                             cells=cells,row_index_candidate=None,original_members=[],
                             column_role_candidates=[],provenance=source,unresolved_items=[]))
    rows.sort(key=lambda r:(-r['cells'][0]['polygon'][2][1],r['cells'][0]['polygon'][0][0],r['row_id']))
    for obj in objects:
        if obj['handle'] in boundary_handles or obj['kind'] in ('TABLE','ACAD_TABLE'):
            continue
        b=extent(obj)
        candidates=[]
        for row in rows:
            for cell in row['cells']:
                loc=location(b,cell['polygon']) if b else 'outside'
                if loc!='outside':
                    candidates.append((loc,cell,row))
        if (len(candidates)==1 and candidates[0][0]=='inside' and
            candidates[0][1]['evidence_status']!='unresolved' and not obj.get('unlocated_extent')):
            _,cell,row=candidates[0]
            cell['members'].append(obj['handle'])
            row['original_members'].append(obj['handle'])
        else:
            ids=[c['cell_id'] for _,c,_ in candidates]
            reason=('extent_unverified' if obj.get('unlocated_extent') else
                    'crossing_or_uncertain_cell' if ids else 'no_closed_cell')
            issues.append(dict(handle=obj['handle'],reason=reason,candidate_cells=ids))
            if b and not obj.get('unlocated_extent'):
                for row in rows:
                    low,high=row['y_interval']
                    if (low+EPS<b[1]<=b[3]<high-EPS and all(
                        any(x-EPS<=b[0]<=b[2]<=xx+EPS for x,xx,_ in spans)
                        for spans in row['horizontal_spans'].values())):
                        row['row_only_candidates'].append(obj['handle'])
            for _,_,row in candidates:
                if obj['handle'] not in row['unresolved_items']:
                    row['unresolved_items'].append(obj['handle'])
    for index,row in enumerate(rows):
        row['row_index_candidate']=index
        statuses={c['evidence_status'] for c in row['cells']}
        row['evidence_status']=('unresolved' if 'unresolved' in statuses else 'ambiguous'
                                if 'ambiguous' in statuses or row['unresolved_items'] else
                                'unresolved' if row['row_only_candidates'] else 'bounded')
    header_candidates(rows,members)
    native=[o['handle'] for o in objects if o['kind'] in ('ACAD_TABLE','TABLE')]
    kind=('drawn_grid' if any(c['evidence_status']!='unresolved' for r in rows for c in r['cells'])
          else 'incomplete_grid_candidate' if horiz or vert else 'ordinary_arrangement')
    if native:
        kind='mixed_region' if rows else 'native_table'
    return dict(NativeLegendRowEvidenceVersion=1,legend_region_id=region,region_name=name,
                window_wcs=window,plane_z=z,region_kind=kind,rows=rows,objects=members,
                drawn_tables=sorted(tables,key=lambda t:t['table_id']),native_table_handles=native,
                unresolved_items=issues,provenance=source)
