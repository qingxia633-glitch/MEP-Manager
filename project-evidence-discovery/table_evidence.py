"""TABLE observations only; never engineering facts or binding annotations."""
from copy import deepcopy
import json
import re
import math
from report_text import text_record
from text_layout import layout_record

EXPORTER='2.6-table-cell-evidence-v1'

def values(text,key):return re.findall(r'^'+re.escape(key)+r'=(.*?)\r?$',text,re.M)
def one(text,key):
    x=values(text,key);return x[0] if len(x)==1 else None
def getter(text,key):
    status=one(text,key+'.Status');status=status.strip('"') if status else 'missing'
    raw=one(text,key+'.Value');source=one(text,key+'.Source')
    out={'status':status,'raw_serialized_value':raw,'value':None,'source':source,'error':one(text,key+'.Error')}
    if status=='read':
        if raw is None or source is None:out['status']='invalid_result'
        else:
            try:
                if key=='Cell.Empty' and raw in (':vlax-false',':vlax-true'):
                    out['value']=raw==':vlax-true'
                elif raw.startswith('(') and raw.endswith(')'):
                    out['value']=[float(x) for x in raw[1:-1].split()]
                    if not all(math.isfinite(x) for x in out['value']):raise ValueError('nonfinite')
                else:out['value']=text_record(raw)['decoded_text'] if raw.startswith('"') else json.loads(raw)
                if out['value'] is None:out['status']='invalid_result'
            except (ValueError,TypeError):out['status']='invalid_result'
    if key=='Cell.Empty' and out['status']=='read' and boolean(out) is None:
        out['status']='invalid_result'
    return out

def boolean(item):
    if item['status']!='read':return None
    v=item['value']
    if type(v)==bool:return v
    if type(v)==int and v in (-1,0):return v==-1
    return {'true':True,'false':False}.get(v) if isinstance(v,str) else None

def table_record(record,identity,provenance,exporter):
    result={'identity':deepcopy(identity),'provenance':deepcopy(provenance),'cells':[],
            'raw_table_record':record,'acquisition_status':'missing','row_count':None,'column_count':None,
            'table_evidence_version':one(record,'TableEvidenceVersion'),'gaps':[],
            'multiple_contents_status':'unsupported','cell_geometry_status':'unresolved'}
    if result['table_evidence_version'] is None:return result
    if result['table_evidence_version']!='"1"' or exporter!=EXPORTER:
        result['acquisition_status']='unsupported';return result
    result['table_evidence_version']='1'
    if (identity.get('parent_path')!=[] or identity.get('space')!='ModelSpace' or
        not all(isinstance(identity.get(k),str) and identity[k].strip()
                for k in ('project_id','drawing_ref','snapshot_id','table_handle'))):
        result['acquisition_status']='unresolved';result['gaps'].append('identity_or_scope_missing');return result
    metadata={k:getter(record,'Table.'+k) for k in ('Rows','Columns','StyleName','InsertionPoint')}
    result['metadata']=metadata
    result['bounds']=layout_record(re.sub(r'^Table\.', '', record, flags=re.M),'TEXT')['bounds']
    for label,name,field in [('RowIndex','row_heights','RowHeight'),('ColumnIndex','column_widths','ColumnWidth')]:
        result[name]=[{'index_raw':one(chunk,'Table.'+label),'evidence':getter(chunk,'Table.'+field)}
                      for chunk in re.split(r'(?m)(?=^Table\.'+label+'=)',record)[1:]]
    rows,cols=metadata['Rows']['value'],metadata['Columns']['value']
    if not all(metadata[k]['status']=='read' for k in ('Rows','Columns')) or any(type(n)!=int or n<=0 for n in (rows,cols)):
        result['acquisition_status']='unavailable';return result
    result.update(row_count=rows,column_count=cols,acquisition_status='partial')
    # Do not allocate a grid from untrusted dimensions; inspect only acquired cells.
    chunks=re.findall(r'^TableCell_BEGIN\r?\n(.*?)^TableCell_END\r?$',record,re.M|re.S)
    if len(chunks)!=record.count('TableCell_BEGIN'):
        result['gaps'].append('incomplete_cell_record')
    seen=set()
    for chunk in chunks:
        try:r=int(one(chunk,'Cell.Row'));c=int(one(chunk,'Cell.Column'))
        except (TypeError,ValueError):result['acquisition_status']='invalid_result';continue
        if not (0<=r<rows and 0<=c<cols):result['acquisition_status']='invalid_result';continue
        if (r,c) in seen:result['acquisition_status']='conflicting';continue
        seen.add((r,c));cid=dict(identity,row_index=r,column_index=c)
        fields={k:getter(chunk,'Cell.'+k) for k in ('Type','ContentType','Text','Empty','FieldId','BlockId','Merged','TextStyle','TextHeight','Alignment')}
        typ=fields['Type']['value'];ct=fields['ContentType']['value'];empty=boolean(fields['Empty'])
        merged=boolean(fields['Merged']);fid=fields['FieldId']['value']
        kind='block' if typ==2 or ct==4 else 'field' if ct==2 or (type(fid)==int and fid>0) else 'empty' if empty is True else 'text_observation' if typ==1 else 'unknown'
        text=fields['Text']['value'] if kind not in ('block','unknown') and isinstance(fields['Text']['value'],str) else None
        cell={'identity':cid,'row_index':r,'column_index':c,'fields':fields,
              'raw_content':fields['Text']['raw_serialized_value'],'decoded_text':text,
              'text_decode_status':fields['Text']['status'] if text is not None else 'unsupported' if kind=='block' else 'unavailable',
              'cell_type':typ,'content_type':ct,'content_kind':kind,
              'merged_status':'merged' if merged is True else 'not_merged' if merged is False else 'unresolved',
              'merged_region':None,'master_cell_identity':None,'independent_content_candidate':False,
              'field_provenance':'missing','formula_status':'unresolved','static_text_provenance_established':False,
              'acquisition_status':'unavailable' if fields['Type']['status']!='read' or (kind!='block' and fields['Text']['status']!='read') else 'partial',
              'provenance':deepcopy(provenance)}
        if merged is True:
            raw=one(chunk,'Cell.MergeRange') or ''
            try:
                region=[int(x) for x in raw.strip('()').split()]
                a,b,d,e=region
                assert raw.startswith('(') and raw.endswith(')') and 0<=a<=r<=b<rows and 0<=d<=c<=e<cols
                cell.update(merged_region=region,master_cell_identity=dict(identity,row_index=a,column_index=d))
            except (ValueError,AssertionError):result['acquisition_status']='invalid_result';cell['merged_status']='unresolved'
        if empty is True and text not in ('',None):
            result['acquisition_status']='conflicting';cell['acquisition_status']='conflicting'
        result['cells'].append(cell)
    if len(seen)!=rows*cols:result['gaps'].append('cell_grid_incomplete')
    indexed={(c['row_index'],c['column_index']):c for c in result['cells']}
    for cell in result['cells']:
        if cell['master_cell_identity']:
            m=cell['master_cell_identity'];master=indexed.get((m['row_index'],m['column_index']))
            if master is None or master['merged_region']!=cell['merged_region']:
                result['acquisition_status']='conflicting';result['gaps'].append('merge_master_inconsistent')
    if one(record,'TableEvidenceComplete')!='true':result['gaps'].append('completion_missing')
    result['gaps'].append('multiple_contents_and_field_provenance_unresolved')
    return result

def consolidate_tables(tables):
    groups={}
    for table in tables:groups.setdefault(json.dumps(table['identity'],sort_keys=True),[]).append(table)
    for group in groups.values():
        if len(group)>1:
            for table in group:table['acquisition_status']='conflicting';table['gaps'].append('duplicate_table_identity')
    return tables
