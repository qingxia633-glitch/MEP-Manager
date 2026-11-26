"""Read top-level native records and assign spatial review dispositions before recognition."""
import math
import re
from collections import Counter
from inventory import relation


def field(record,key):
    m=re.search(r'(?m)^'+re.escape(key)+r'=(.*?)\r?$',record)
    return m[1].strip('"') if m else None


def point(text):
    if not text or not text.startswith('(') or not text.endswith(')'):
        return None
    try:
        p=tuple(map(float,text[1:-1].split()))
        return p if len(p)==3 and all(map(math.isfinite,p)) else None
    except ValueError:
        return None


def segment_hits(a,b,box):
    # Slab clipping, including a tangent or endpoint on the frame.
    lo,hi=0.,1.
    for x,y,mn,mx in zip(a[:2],b[:2],box[:2],box[2:]):
        delta=y-x
        if delta==0:
            if not mn<=x<=mx:
                return False
        else:
            p,q=sorted(((mn-x)/delta,(mx-x)/delta))
            lo,hi=max(lo,p),min(hi,q)
            if lo>hi:
                return False
    return True


def envelope(lo,hi,box):
    if any(h<l for h,l in zip(hi,lo)):
        return 'unresolved'
    if any(h<m or l>M for l,h,m,M in zip(lo,hi,box[:2],box[2:])):
        return 'outside'
    if all(m<l<=h<M for l,h,m,M in zip(lo,hi,box[:2],box[2:])):
        return 'inside'
    return 'unresolved'


def locate(record,kind,box):
    if kind=='INSERT':
        p=point(field(record,'Insertion_WCS'))
        return relation(p,box),p,'native INSERT insertion WCS'
    if kind in ('TEXT','MTEXT'):
        p=point(field(record,'Position_WCS'))
        lo,hi=[point(field(record,k)) for k in ('bboxMin','bboxMax')]
        if lo and hi and field(record,'bboxFrame')=='WCS' and field(record,'bboxStatus')=='read':
            return envelope(lo[:2],hi[:2],box),p,'text WCS bounds'
        return relation(p,box),p,'text anchor only'
    if kind in ('LINE','LWPOLYLINE'):
        pts=([point(field(record,k)) for k in ('Start_WCS','End_WCS')] if kind=='LINE'
             else [point(v) for v in re.findall(r'(?m)^Vertex_WCS=(.*)$',record)])
        if len(pts)<2 or None in pts:
            return 'unresolved',None,'missing native path'
        if kind=='LWPOLYLINE':
            bulges=re.findall(r'Width_or_bulge_DXF=\(42 \. ([^)]*)\)',record)
            if len(bulges)!=len(pts) or any(not re.fullmatch(r'[-+]?0+(?:\.0+)?',v) for v in bulges):
                return 'unresolved',pts[0],'curved or incomplete path extent'
            if field(record,'Closed')=='T':
                pts.append(pts[0])
        if all(relation(p,box)=='inside' for p in pts):
            return 'inside',pts[0],'WCS path centerline'
        crossing=any(segment_hits(a,b,box) for a,b in zip(pts,pts[1:]))
        return ('on_boundary' if crossing else 'outside'),pts[0],'WCS path centerline'
    if kind in ('CIRCLE','ARC','POINT','ATTDEF'):
        pts=re.findall(r'(?m)^Raw_DXF=\(10 ([^()]+)\)$',record)
        p=point('('+pts[0]+')') if len(pts)==1 else None
        if not p or point(field(record,'Normal_DXF210'))!=(0.,0.,1.):
            return 'unresolved',None,'unqualified native point or normal'
        if kind in ('POINT','ATTDEF'):
            return relation(p,box),p,'native placement +Z'
        radii=re.findall(r'(?m)^Raw_DXF=\(40 \. ([^()]+)\)$',record)
        rad=float(radii[0]) if len(radii)==1 else 0
        if not math.isfinite(rad) or rad<=0:
            return 'unresolved',p,'unqualified radius'
        lo=[x-rad for x in p[:2]]; hi=[x+rad for x in p[:2]]
        return envelope(lo,hi,box),p,'conservative full-circle envelope'
    return 'unresolved',None,'no supported WCS locator'


def survey(text,scope):
    starts=list(re.finditer(r'(?m)^EntityHandle=',text))
    header=text[:starts[0].start()] if starts else text
    if (field(header,'AcquisitionMode')!='ModelSpaceTopLevelAllLayers'
        or field(header,'ModelSpaceTopLevel')!='included' or field(header,'NestedBlocks')!='not expanded'
        or not (field(header,'AllLayers') or '').startswith('included')
        or field(text,'SelectedEntityTotal')!=str(len(starts)) or field(text,'ReadErrorCount')!='0'
        or not text.rstrip().splitlines()[-1].startswith('END_OF_REPORT:')):
        raise ValueError('global report incomplete')
    rows=[];records={};line=header.count('\n')+1
    for i,start in enumerate(starts):
        rec=text[start.start():starts[i+1].start() if i+1<len(starts) else len(text)]
        h,kind=field(rec,'EntityHandle'),field(rec,'DXF_Type')
        if not h or not kind or h in records:
            raise ValueError('incomplete or duplicate native identity')
        pos=field(rec,'Insertion_WCS') if kind=='INSERT' else None
        membership,anchor,basis=locate(rec,kind,scope['scope_boundary'])
        tr=re.findall(r'(?m)^BlockTransform_or_Array_DXF=(.*)$',rec) if pos else []
        name=field(rec,'BlockName') if kind=='INSERT' else None
        if kind=='INSERT':
            shape='block_unclassified'
            if name and re.search(r'图签|标注|图框|轴号',name):
                shape='annotation_block_name_candidate'
            elif name and re.search(r'建筑|门窗|柱|墙',name):
                shape='architectural_block_name_candidate'
        else:
            shape={'TEXT':'annotation_carrier','MTEXT':'annotation_carrier','ATTDEF':'definition_metadata'}.get(kind,'independent_geometry_unclassified')
        row=dict(project_id=scope['project_id'],drawing_instance_id=scope['drawing_instance_id'],
                 snapshot=scope['report_sha256'],parent_path=[],handle=h,entity_type=kind,
                 scope_id=scope['scope_id'],scope_version=scope['scope_version'],floor_id=scope['floor_id'],
                 floor_status=scope['floor_status'],coordinate_system=scope['coordinate_system'],
                 unit=scope['unit'],boundary_relation=membership,spatial_membership_status=
                 {'inside':'included','outside':'outside','on_boundary':'pending','unresolved':'unresolved'}[membership],
                 location=anchor,location_basis=basis,insertion_wcs=pos,block_name=name,
                 block_definition_identity=None,instance_transform=tr,normal=field(rec,'Normal_DXF210'),
                 survey_kind=shape,nested_coverage='not_expanded' if kind=='INSERT' else None,
                 provenance=dict(report_sha256=scope['report_sha256'],line=line,handle=h),
                 inventory_class='confirmed_non_device' if kind=='ATTDEF' else 'unclassified',
                 device_status='unresolved',candidate_types=[])
        rows.append(row);records[h]=rec;line+=rec.count('\n')
    return sorted(rows,key=lambda r:r['handle']),records
