"""Offline GeometryConnectionResolver v0.1. No electrical or quantity inference.

DrawingContext adapts existing MEPFULLREAD and one-level DXF probe reports.
Missing definitions are explicit; this module never invokes AutoCAD.
"""
import hashlib
import math
import re
from pathlib import Path


def _field(text, key):
    m = re.search(r'^' + re.escape(key) + r'=(.*?)\r?$', text, re.M)
    return m[1].strip().strip('"') if m else None


def _point(value):
    if value is None:
        return None
    return [float(v) for v in value.strip('()').split()]


def _dxf(text, code):
    return re.findall(r'^DXF:' + str(code) + r'=(.*?)\r?$', text, re.M)


def _entity(text):
    """Read direct DXF geometry only, excluding attached attribute subentities."""
    text = text.split('Subentity_BEGIN')[0]
    typ = _field(text, 'DXF_Type')
    e = dict(type=typ, handle=_field(text, 'EntityHandle'))
    def first(code, default=None):
        values = _dxf(text, code)
        return values[0].strip('"') if values else default
    e['hidden'] = first(60, '0') != '0'
    e['normal'] = _point(first(210, '(0 0 1)'))
    if typ == 'INSERT':
        e.update(block=first(2), insertion=_point(first(10)),
                 scale=[float(first(c, '1')) for c in (41,42,43)],
                 rotation=float(first(50, '0')), dynamic=None,
                 array=any(int(first(c,'1'))>1 for c in (70,71)))
    elif typ in ('POINT', 'CIRCLE'):
        e['point'] = _point(first(10))
        if typ == 'CIRCLE':
            e['radius'] = float(first(40, 'nan'))
    elif typ == 'LINE':
        e['vertices'] = [_point(first(10)), _point(first(11))]
    elif typ == 'LWPOLYLINE':
        z = float(first(38, '0'))
        e['vertices'] = [[*_point(p)[:2], z] for p in _dxf(text,10)]
        e['closed'] = bool(int(first(70, '0')) & 1)
        e['bulges'] = [float(v) for v in _dxf(text,42)]
        e['width'] = max([abs(float(v)) for c in (40,41,43) for v in _dxf(text,c)] or [0])
    return e


class DrawingContext:
    """Entities keyed by handle, definitions keyed by exact block table name.

    Normalized provider definitions must explicitly state completeness and dynamic
    status. POLYLINE vertices from an external provider must already include all
    VERTEX subentities; the report adapter conservatively leaves POLYLINE unknown.
    """
    def __init__(self, entities, definitions, provenance, project_id=None, drawing_ref=None):
        self.entities, self.definitions, self.provenance = entities, definitions, provenance
        self.project_id,self.drawing_ref=project_id,drawing_ref

    @classmethod
    def from_reports(cls, snapshot, probes):
        entities, definitions, provenance = {}, {}, []
        def read(path):
            data = Path(path).read_bytes()
            provenance.append(dict(path=str(path), sha256=hashlib.sha256(data).hexdigest()))
            return data.decode('utf-8-sig')
        raw = read(snapshot)
        drawing = _field(raw,'DWG')
        for rec in re.split(r'(?m)(?=^EntityHandle=)', raw):
            h, typ = _field(rec,'EntityHandle'), _field(rec,'DXF_Type')
            if not h:
                continue
            e = dict(handle=h,type=typ)
            if typ == 'INSERT':
                values = {}
                for code in (41,42,43,50):
                    m = re.search(r'BlockTransform_or_Array_DXF=\(' + str(code) + r' \. ([^)]+)\)',rec)
                    values[code] = float(m[1]) if m else None
                e.update(block=_field(rec,'BlockName'), insertion=_point(_field(rec,'Insertion_OCS')),
                         scale=[values[c] for c in (41,42,43)],rotation=values[50],
                         normal=_point(_field(rec,'Normal_DXF210')),
                         dynamic={':vlax-false':False, ':vlax-true':True}.get(_field(rec,'IsDynamicBlock')),
                         array=any(int(m)>1 for m in re.findall(r'BlockTransform_or_Array_DXF=\((?:70|71) \. (\d+)\)',rec)))
            e['vertices'] = [_point(p) for p in re.findall(r'^Vertex_WCS=(.*?)\r?$',rec,re.M)]
            if typ == 'LWPOLYLINE':
                e['closed'] = {'T':True, 'nil':False}.get(_field(rec,'Closed'))
            if typ == 'LINE' and not e['vertices']:
                start,end = _field(rec,'Start_WCS'),_field(rec,'End_WCS')
                if start and end:
                    e['vertices']=[_point(start),_point(end)]
            entities[h] = e
        for path in probes:
            report = read(path)
            if not drawing or _field(report,'DWG') != drawing:
                raise ValueError('Probe/snapshot DWG provenance missing or different: '+str(path))
            for block in report.split('Block_BEGIN=')[1:]:
                name = block.splitlines()[0].strip('"\r')
                chunks = block.split('Entity_END')
                children = [_entity(c) for c in chunks if _field(c,'DXF_Type')]
                expected = _field(block,'DirectEntityCount')
                complete = (expected is not None and int(expected)==len(children) and 'Block_END' in block
                            and not any(x in block for x in ['ENTITY_UNREADABLE','TRANSFORM_ERROR','DETAIL_ERROR']))
                # ATTDEF getter extents errors do not invalidate unrelated raw geometry.
                for c in chunks:
                    if 'BoundsError=' in c and _field(c,'DXF_Type') not in ('ATTDEF','ATTRIB','TEXT','MTEXT'):
                        complete = False
                d = dict(base=_point(_field(block,'DefinitionDXF:10')),entities=children,
                         complete=complete,dynamic={':vlax-false':False,':vlax-true':True}.get(_field(block,'DefinitionIsDynamicBlock')),
                         source=str(path))
                if name in definitions and {k:v for k,v in definitions[name].items() if k!='source'} != {k:v for k,v in d.items() if k!='source'}:
                    # Ambiguous competing definitions must not silently overwrite one another.
                    definitions[name]['complete'] = False
                    definitions[name]['conflicting'] = True
                else:
                    definitions[name] = d
            # Resolved root reference DXF has better precision than rounded snapshot fields.
            if _field(report,'DefinitionPathStatus') == 'resolved':
                h = _field(report,'ParentReferenceDXF:5')
                if h in entities:
                    e = entities[h]
                    def parent_number(code):
                        value=_field(report,'ParentReferenceDXF:'+str(code))
                        return float(value) if value is not None else None
                    e.update(insertion=_point(_field(report,'ParentReferenceDXF:10')),
                             scale=[parent_number(c) for c in (41,42,43)],
                             rotation=parent_number(50),
                             normal=_point(_field(report,'ParentReferenceDXF:210')))
        return cls(entities,definitions,provenance,drawing_ref=drawing)


def _transform(p, chain):
    """Child-to-parent application; chain is recorded outermost first."""
    q = list(p)
    if len(q) == 2:
        q.append(0)
    for t in reversed(chain):
        x,y,z = [(q[i]-t['base'][i])*t['scale'][i] for i in range(3)]
        c,s = math.cos(t['rotation']),math.sin(t['rotation'])
        q = [t['insertion'][0]+c*x-s*y,t['insertion'][1]+s*x+c*y,t['insertion'][2]+z]
    return q


def _nearest_segment(p,a,b):
    v = [b[i]-a[i] for i in range(3)]
    denom = v[0]**2+v[1]**2
    t = max(0,min(1,sum((p[i]-a[i])*v[i] for i in range(2))/denom)) if denom else 0
    return [a[i]+t*v[i] for i in range(3)],t


def resolve_connection(edge_handle, edge_endpoint, target_insert_handle, context,
                       connection_xy_tolerance, max_depth=16):
    """Classify XY geometry only. Unknown Z meaning cannot veto XY contact.

    Only explicit POINT/line endpoints/open-polyline endpoints are anchors.
    Boundary/width-envelope contact is partial. Missing/unsupported content
    prevents rejection; a proven anchor can still support local contact.
    """
    tol = float(connection_xy_tolerance)
    ep = list(edge_endpoint)
    if len(ep)!=3 or not all(math.isfinite(v) for v in ep) or not math.isfinite(tol) or tol<=0:
        raise ValueError('Finite XYZ endpoint and positive finite tolerance required')
    anchors, surfaces, issues, chains = [], [], [], []
    source = context.entities.get(edge_handle, {})
    vertices = source.get('vertices', [])
    endpoint_source = None
    readable = (source.get('type') in ('LINE','LWPOLYLINE','POLYLINE') and
                isinstance(vertices,list) and len(vertices)>=2 and
                all(isinstance(p,(list,tuple)) and len(p)==3 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in vertices) and
                source.get('closed',False) is False)
    if readable:
        matches = [(i,math.dist(ep,vertices[i])) for i in (0,len(vertices)-1) if math.dist(ep,vertices[i])<=tol]
        if matches:
            index,residual = min(matches,key=lambda m:m[1])
            endpoint_source = dict(edge_handle=edge_handle,source_entity_type=source['type'],endpoint_index=index,
                                   requested_wcs=list(ep),verified_endpoint_wcs=list(vertices[index]),
                                   source_match_residual=residual,provenance=context.provenance)
            ep=list(vertices[index])
    depth = 0
    def candidate(e,path,local,world,chain,anchor=False,halfwidth=0):
        if len(world)!=3 or not all(math.isfinite(v) for v in world):
            raise ValueError('Nonfinite geometry')
        item = dict(source_entity_handle=e['handle'],source_entity_type=e['type'],
                    source_definition_path=path+[e['handle']],local_coordinate=local,
                    transformed_wcs=world,xy_distance=math.dist(ep[:2],world[:2]),
                    xyz_distance=math.dist(ep,world),transform_chain=chain,
                    anchor=anchor,width_envelope_halfwidth=halfwidth)
        (anchors if anchor else surfaces).append(item)
    def visit(inst,path,chain,stack):
        nonlocal depth
        name = inst.get('block'); definition = context.definitions.get(name)
        depth = max(depth,len(stack)+1)
        if len(stack)>=max_depth or name in stack:
            issues.append('cycle_or_depth_limit:'+str(name));return
        if not definition:
            issues.append('missing_definition:'+str(name));return
        if definition.get('dynamic') is not False or inst.get('dynamic') is True or definition.get('conflicting'):
            issues.append('dynamic_or_conflicting_definition:'+str(name));return
        if inst.get('array'):
            issues.append('unsupported_insert_array:'+str(inst.get('handle')));return
        required = [inst.get('insertion'),inst.get('scale'),definition.get('base'),inst.get('normal')]
        if any(v is None or len(v)!=3 or any(x is None or not math.isfinite(x) for x in v) for v in required) or inst.get('rotation') is None:
            issues.append('incomplete_transform:'+str(inst.get('handle')));return
        if inst['normal'] != [0,0,1] or any(x==0 for x in inst['scale']) or not math.isfinite(inst['rotation']):
            issues.append('unsupported_normal_or_degenerate_transform');return
        if not definition.get('complete'):
            issues.append('incomplete_definition:'+str(name))
        t = {k:inst[k] for k in ('handle','insertion','scale','rotation','normal')}
        t.update(base=definition['base'],definition=name)
        chain = chain+[t]; chains.append(chain)
        for e in definition['entities']:
            typ = e.get('type')
            if typ in ('ATTRIB','ATTDEF','TEXT','MTEXT'):
                continue
            if e.get('hidden'):
                issues.append('hidden_geometry:'+str(e.get('handle')));continue
            if typ == 'INSERT':
                visit(e,path+[e['handle']],chain,stack+[name]);continue
            if e.get('normal',[0,0,1]) != [0,0,1]:
                issues.append('unsupported_entity_normal:'+str(e.get('handle')));continue
            try:
                if typ == 'POINT':
                    p=e['point'];candidate(e,path,p,_transform(p,chain),chain,True)
                elif typ in ('LINE','LWPOLYLINE','POLYLINE'):
                    pts=e['vertices']
                    if len(pts)<2 or any(v is None or len(v)!=3 for v in pts) or any(e.get('bulges',[])):
                        raise ValueError('missing vertices or curved polyline')
                    closed=e.get('closed',False)
                    if not closed:
                        for p in (pts[0],pts[-1]):candidate(e,path,p,_transform(p,chain),chain,True)
                    pairs=list(zip(pts,pts[1:]))+([(pts[-1],pts[0])] if closed else [])
                    # Conservative affine width envelope: prevents false rejection under nonuniform scales.
                    width=abs(e.get('width',0))/2
                    if not math.isfinite(width):
                        raise ValueError('nonfinite width')
                    for tr in chain:width*=max(abs(v) for v in tr['scale'][:2])
                    for a,b in pairs:
                        q,u=_nearest_segment(ep,_transform(a,chain),_transform(b,chain))
                        local=[a[i]+u*(b[i]-a[i]) for i in range(3)]
                        candidate(e,path,local,q,chain,False,width)
                elif typ == 'CIRCLE':
                    if any(abs(abs(tr['scale'][0])-abs(tr['scale'][1]))>1e-12 for tr in chain):
                        raise ValueError('nonuniform circle')
                    center=_transform(e['point'],chain);r=e['radius']
                    if not math.isfinite(r) or r<=0:raise ValueError('invalid circle')
                    for tr in chain:r*=abs(tr['scale'][0])
                    d=math.dist(ep[:2],center[:2]);u=[(ep[i]-center[i])/d for i in range(2)] if d else [1,0]
                    q=[center[0]+r*u[0],center[1]+r*u[1],center[2]]
                    local=q[:]
                    for tr in chain:
                        x,y,z=[local[i]-tr['insertion'][i] for i in range(3)]
                        c,s=math.cos(tr['rotation']),math.sin(tr['rotation'])
                        local=[(c*x+s*y)/tr['scale'][0]+tr['base'][0],
                               (-s*x+c*y)/tr['scale'][1]+tr['base'][1],
                               z/tr['scale'][2]+tr['base'][2]]
                    candidate(e,path,local,q,chain)
                else:
                    issues.append('unsupported_entity:'+str(typ)+':'+str(e.get('handle')))
            except (KeyError,TypeError,ValueError,OverflowError):
                issues.append('incomplete_or_unsupported_geometry:'+str(e.get('handle')))
    target=context.entities.get(target_insert_handle)
    if target and target.get('type')=='INSERT' and not target.get('hidden'):
        visit(target,[target_insert_handle],[],[])
    else:
        issues.append('target_insert_missing')
    anchors.sort(key=lambda x:x['xy_distance']);surfaces.sort(key=lambda x:x['xy_distance'])
    hits=[a for a in anchors if a['xy_distance']<=tol]
    touch=[s for s in surfaces if s['xy_distance']<=tol+s['width_envelope_halfwidth']]
    if endpoint_source is None:
        status,reason='unresolved','source_edge_endpoint_not_verified'
        issues.append(reason)
    elif hits:status,reason='supported','real_anchor_within_xy_tolerance'
    elif touch:status,reason='partial','real_geometry_or_conservative_width_envelope_contact_not_anchor'
    elif issues or not (anchors or surfaces):status,reason='unresolved','missing_or_unsupported_evidence'
    else:status,reason='rejected','complete_geometry_disjoint_in_xy; indirect_relationship_not_evaluated'
    return dict(edge_handle=edge_handle,edge_endpoint_wcs=ep,endpoint_source=endpoint_source,target_handle=target_insert_handle,
                evidence_identity={'project_id':context.project_id,'drawing_ref':context.drawing_ref,
                    'edge_parent_path':source.get('parent_path',[]),'target_parent_path':(target or {}).get('parent_path',[])},
                target_block_name=target.get('block') if target else None,
                candidate_geometry=hits or anchors,nearest_geometry=surfaces[0] if surfaces else None,
                geometry_resolution_status='incomplete' if issues else 'complete',definition_depth=depth,
                transform_chain=chains,tolerance={'connection_xy_tolerance':tol,'unit':'drawing_units'},
                geometric_connection_status=status,connection_scope='direct_xy_geometry',
                z_semantics_status='unresolved',reason=reason,issues=issues,provenance=context.provenance,
                assumptions=['XY geometric contact only; not electrical terminal identity',
                             'Z semantic meaning unresolved; xyz_distance is descriptive only',
                             'Rejection applies only to direct geometric contact',
                             'Instance attributes and definition text never used as connection anchors'])
