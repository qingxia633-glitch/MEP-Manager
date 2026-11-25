"""Read verified ModelSpace evidence once; write a new structural evidence result."""
import argparse
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'project-evidence-discovery'))
from annotations import corrected_reference, field
from report_manifest import verify_manifest
from report_text import serialized_field, text_record
from line_style import style_evidence
from text_layout import layout_record
from table_evidence import table_record
from field_provenance import field_record
from rows import EPS, overlaps, reconstruct


def point(literal):
    if not literal or not re.fullmatch(r'\([^()]+\)',literal):
        return None
    try:
        coords=list(map(float,literal[1:-1].split()))
    except ValueError:
        return None
    return coords if len(coords)==3 and all(map(math.isfinite,coords)) else None


def text_evidence(record, kind, identity, source, version):
    key='AttributeText_RAW' if kind=='ATTRIB' else 'Text_RAW'
    text=text_record(serialized_field(record,key))
    layout=layout_record(record,kind)
    observed=field_record(record,identity,kind,text['decoded_text'],text['text_decode_status'],
                          [source],version)
    return dict(**text, layout=layout, field_evidence=observed)


def locate(record, kind):
    if kind in ('LINE','LWPOLYLINE'):
        points=([point(field(record,k)) for k in ('Start_WCS','End_WCS')] if kind=='LINE'
                else [point(v) for v in re.findall(r'(?m)^Vertex_WCS=(.*?)\r?$',record)])
        if len(points)<2 or None in points:
            return None
        bulges=re.findall(r'(?m)^Width_or_bulge_DXF=\(42 \. ([^)]*)\)',record)
        straight=all(re.fullmatch(r'[-+]?0+(?:\.0+)?',v) for v in bulges)
        return dict(points=points, straight=straight, closed=field(record,'Closed')=='T',
                    unlocated_extent=not straight)
    if kind in ('TEXT','MTEXT'):
        if field(record,'bboxStatus')=='read' and field(record,'bboxFrame')=='WCS':
            a,b=[point(field(record,k)) for k in ('bboxMin','bboxMax')]
            if a and b and all(x<=y for x,y in zip(a,b)):
                return dict(points=[a,b],membership_basis='WCS bounding box')
        p=point(field(record,'Position_WCS'))
        return dict(points=[p],unlocated_extent=True) if p else None
    if kind=='INSERT':
        p=point(field(record,'Insertion_WCS'))
        return dict(points=[p],membership_basis='INSERT anchor only') if p else None
    if kind in ('TABLE','ACAD_TABLE') and field(record,'Table.InsertionPoint.Status')=='read':
        p=point(field(record,'Table.InsertionPoint.Value'))
        return dict(points=[p],membership_basis='native TABLE anchor') if p else None
    return None


def read_region(path,manifest,project,name,window,z=0):
    path=Path(path)
    data=path.read_bytes()
    verified=verify_manifest(data,path,'utf-8-sig',manifest)
    raw=data.decode('utf-8-sig')
    starts=list(re.finditer(r'(?m)^EntityHandle=',raw))
    header=raw[:starts[0].start()] if starts else raw
    if (not project.strip() or field(header,'AcquisitionMode')!='ModelSpaceTopLevelAllLayers'
        or field(header,'NestedBlocks')!='not expanded' or field(header,'ModelSpaceTopLevel')!='included'
        or not (field(header,'AllLayers') or '').startswith('included')
        or not raw.rstrip().splitlines()[-1].startswith('END_OF_REPORT:')
        or field(raw,'ReadErrorCount')!='0' or field(raw,'SelectedEntityTotal')!=str(len(starts))):
        raise ValueError('incomplete report or unsupported acquisition scope')
    drawing=(field(header,'DWG') or '').replace('\\','/').split('/')[-1]
    if not drawing:
        raise ValueError('missing drawing identity')
    corrected_reference(drawing,None)
    source=dict(project_id=project,drawing=drawing,snapshot_id=verified['report_sha256'])
    version=field(header,'ExtractorVersion')
    if version not in {'2.4-leader-evidence-v1','2.5-line-style-evidence-v1',
                       '2.6-table-cell-evidence-v1','2.7-field-provenance-v1','2.8-field-graph-evidence-v1'}:
        raise ValueError('unsupported report version')
    seen=set()
    records=[]
    gaps={}
    line=header.count('\n')+1
    for i,m in enumerate(starts):
        record=raw[m.start():starts[i+1].start() if i+1<len(starts) else len(raw)]
        first=line
        line+=record.count('\n')
        h=field(record,'EntityHandle')
        typ=field(record,'DXF_Type')
        if not h or h in seen:
            raise ValueError('missing or duplicate top-level handle')
        seen.add(h)
        geo=locate(record,typ)
        if geo is None:
            gaps[typ]=gaps.get(typ,0)+1
            continue
        pts=geo['points']
        xs,ys,zs=zip(*pts)
        box=[min(xs),min(ys),max(xs),max(ys)]
        if not overlaps(box,window) or min(zs)>z+EPS or max(zs)<z-EPS:
            continue
        if any(abs(v-z)>EPS for v in zs):
            geo.update(straight=False,unlocated_extent=True)
        ident=dict(project_id=project,drawing_ref=drawing,snapshot_id=source['snapshot_id'],
                   parent_path=[],handle=h)
        prov=dict(**ident,record_start_line=first,report_file=path.name)
        obj=dict(handle=h,kind=typ,bounds=box,identity=ident,layer=field(record,'Layer'),
                 provenance=prov,**geo)
        obj['style']=style_evidence(record,header,dict(ident,drawing=drawing),[prov])
        if typ in ('TABLE','ACAD_TABLE'):
            obj['native_table']=table_record(record,dict(ident,table_handle=h,space='ModelSpace'),[prov],version)
        elif typ in ('TEXT','MTEXT'):
            obj.update(text_evidence(record,typ,ident,prov,version))
        elif typ=='INSERT':
            obj['block_name']=field(record,'BlockName')
            obj['attributes']=[]
            for attr in re.split(r'(?m)(?=^AttributeTag=)',record)[1:]:
                ah=field(attr,'AttributeLayout.LayoutEntityHandle')
                owner=field(attr,'AttributeLayout.ParentINSERTHandle')
                aid=dict(ident,parent_path=[h],handle=ah,owner_insert_handle=h)
                obj['attributes'].append(dict(identity=aid,reported_owner=owner,
                    association_status='explicit' if ah and owner==h else 'unresolved',
                    tag=field(attr,'AttributeTag'),**text_evidence(attr,'ATTRIB',aid,prov,version)))
        records.append(obj)
    result=reconstruct(source,name,window,z,records)
    result['report_level_unlocated_by_type']=gaps
    result['scope']='Top-level ModelSpace; unlocated or unsupported records are not evidence of empty cells.'
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--project',required=True)
    parser.add_argument('--region',required=True)
    parser.add_argument('--window',type=float,nargs=4,required=True)
    parser.add_argument('--z',type=float,default=0.)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=read_region(args.report,args.manifest,args.project,args.region,args.window,args.z)
    with args.output.open('x',encoding='utf-8') as out:
        json.dump(result,out,ensure_ascii=False,allow_nan=False,indent=1)
