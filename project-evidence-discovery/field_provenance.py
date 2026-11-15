"""Carrier-qualified Field observations, deliberately outside binding admission."""
from copy import deepcopy
import re
from report_text import text_record
from field_graph import graph_record

EXPORTER='2.7-field-provenance-v1'

def values(raw,key):
    return re.findall(r'^'+re.escape(key)+r'=(.*?)\r?$',raw,re.M)

def scalar(raw,key):
    hits=values(raw,key)
    if len(hits)!=1:return None
    return text_record(hits[0])['decoded_text']

def code_observation(raw):
    status=scalar(raw,'Field.Code.Status') or 'missing'
    literals=values(raw,'Field.Code.Value')
    code=None
    if status=='read':
        if len(literals)!=1 or not scalar(raw,'Field.Code.Source'):status='invalid_result'
        else:
            decoded=text_record(literals[0]);code=decoded['decoded_text']
            if decoded['text_decode_status']!='read' or not code:status='invalid_result'
            elif '%<' in code or '>%' in code:
                depth=0
                for token in re.findall(r'%<|>%',code):
                    depth+=1 if token=='%<' else -1
                    if depth<0:break
                if depth!=0:status='invalid_result'
    if status not in ('read','missing','unavailable','unsupported','unresolved','invalid_result','conversion_error'):
        status='invalid_result'
    return code,status,literals

def field_record(raw,identity,carrier_type,displayed,status,provenance,exporter,present=False):
    code,code_status,literals=code_observation(raw)
    marker=isinstance(displayed,str) and '%<' in displayed
    code_marker=isinstance(code,str) and '%<' in code
    version=scalar(raw,'FieldEvidenceVersion')
    graph_root_observed=(version=='2' and exporter=='2.8-field-graph-evidence-v1'
                         and scalar(raw,'FieldGraph.Root') is not None)
    if not (present or marker or code_marker or graph_root_observed):return None
    out={'field_identity':dict(deepcopy(identity),field_index=0),
         'carrier_identity':deepcopy(identity),'carrier_type':carrier_type,
         'field_presence':'observed' if present or graph_root_observed else 'marker_candidate',
         'displayed_value':displayed if carrier_type=='TABLE_CELL' else None,
         'displayed_value_status':status if carrier_type=='TABLE_CELL' else 'unresolved',
         'carrier_text_observation':displayed,
         'raw_field_code':code,'raw_serialized_field_code':literals,
         'field_code_status':code_status,'field_kind':'unknown_field',
         'referenced_object_identity':[],'referenced_property':None,'reference_status':'unresolved',
         'evaluation_status':'unsupported','mixed_field_text_structure':'unresolved',
         'authored_static_text_established':False,'provenance_strength':'display_only',
         'field_object_handle':scalar(raw,'Field.Handle'),
         'field_graph':graph_record(raw,identity,provenance) if exporter=='2.8-field-graph-evidence-v1' and version=='2' else graph_record('',identity,provenance),
         'raw_field_record':raw,'provenance':deepcopy(provenance),'status':'partial'}
    handle=identity.get('table_handle') or identity.get('handle')
    valid=all(isinstance(identity.get(k),str) and identity[k] for k in ('project_id','drawing_ref','snapshot_id'))
    valid=valid and isinstance(identity.get('parent_path'),list) and isinstance(handle,str) and bool(handle)
    if carrier_type=='TABLE_CELL':
        valid=valid and all(type(identity.get(k))==int and identity[k]>=0 for k in ('row_index','column_index'))
    if not valid or (version is not None and scalar(raw,'Field.CarrierHandle')!=handle):
        out['field_graph']=graph_record('',identity,provenance)
        out.update(status='unresolved',field_code_status='unresolved');return out
    if version is not None and ((version,exporter) not in (('1',EXPORTER),('2','2.8-field-graph-evidence-v1'))):
        out.update(status='unsupported',field_code_status='unsupported');return out
    if version is None:
        out.update(raw_field_code=None,field_code_status='missing');return out
    if code_status=='read':out['provenance_strength']='raw_expression_observed'
    for literal in values(raw,'Field.ReferenceHandle'):
        ref=text_record(literal)['decoded_text']
        if ref and re.fullmatch(r'[0-9A-Fa-f]+',ref):
            out['referenced_object_identity'].append({'project_id':identity['project_id'],
                'drawing_ref':identity['drawing_ref'],'snapshot_id':identity['snapshot_id'],
                'handle':ref,'parent_path':None,'identity_status':'partial',
                'source':'FIELD DXF331; instance path not established'})
    if out['referenced_object_identity']:out['reference_status']='partial'
    return out
