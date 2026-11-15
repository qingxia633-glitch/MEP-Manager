"""Validate carrier-qualified FIELD observations; never resolve engineering meaning."""
from copy import deepcopy
import re
from report_text import text_record

MAX_DEPTH = 16
MAX_NODES = 1024

def graph_record(raw, carrier, provenance):
    reasons=[]
    def items(text,key):
        values=re.findall(r'^'+re.escape(key)+r'=(.*?)\r?$',text,re.M)
        return [text_record(v)['decoded_text'] if v.startswith('"') else
                int(v) if re.fullmatch(r'\d+',v) else None for v in values]
    def one(text,key):
        v=items(text,key)
        return v[0] if len(v)==1 else None
    def identity(handle):
        return {'carrier_identity':deepcopy(carrier),'field_handle':handle}
    out={'version':1,'root_field':None,'nodes':[],'edges':[],'object_references':[],
         'graph_status':'unresolved','graph_complete':False,'unresolved_reasons':reasons,
         'maximum_depth':0,'provenance':deepcopy(provenance)}
    if one(raw,'FieldGraphVersion')!='1':
        reasons.append('graph_missing_or_unsupported_version');return out
    valid=all(isinstance(carrier.get(k),str) and carrier[k] for k in ('project_id','drawing_ref','snapshot_id'))
    valid=valid and isinstance(carrier.get('parent_path'),list) and bool(carrier.get('table_handle') or carrier.get('handle'))
    if not valid:reasons.append('carrier_identity_incomplete')
    if one(raw,'FieldGraph.Status')!='read':reasons.append('exporter_traversal_incomplete')
    root=one(raw,'FieldGraph.Root');out['root_field']=identity(root)
    blocks=re.findall(r'^FieldNode_BEGIN\r?\n(.*?)^FieldNode_END\r?$',raw,re.M|re.S)
    if raw.count('FieldNode_BEGIN')!=len(blocks) or raw.count('FieldNode_END')!=len(blocks):
        reasons.append('malformed_node_envelope')
    if len(blocks)>MAX_NODES:reasons.append('node_limit')
    nodes={}
    for block in blocks[:MAX_NODES]:
        h=one(block,'Node.Handle')
        if not isinstance(h,str) or not re.fullmatch(r'[0-9A-Fa-f]+',h):
            reasons.append('missing_or_invalid_node_handle');continue
        if h in nodes:reasons.append('duplicate_node_identity:'+h);continue
        children=items(block,'Node.Child');refs=items(block,'Node.Reference')
        count=one(block,'Node.ChildCount');rc=one(block,'Node.ReferenceCount')
        errors=[]
        if one(block,'Node.Type') not in ('ACAD_FIELD','FIELD'):errors.append('wrong_object_type')
        if one(block,'Node.Status')!='read':errors.append('node_acquisition_incomplete')
        if not isinstance(one(block,'Node.Evaluator'),str) or not one(block,'Node.Evaluator'):
            errors.append('evaluator_missing')
        if type(count)!=int or count!=len(children):errors.append('child_count_mismatch')
        if type(rc)!=int or rc!=len(refs):errors.append('reference_count_mismatch')
        if len(set(children))!=len(children):errors.append('duplicate_child_identity')
        if len(set(refs))!=len(refs):errors.append('duplicate_reference_identity')
        if any(not isinstance(x,str) or not re.fullmatch(r'[0-9A-Fa-f]+',x) for x in children+refs):errors.append('missing_or_invalid_reference_id')
        code=one(block,'Node.Code');cs=one(block,'Node.CodeStatus')
        if cs!='read' or not isinstance(code,str) or not code:errors.append('field_code_missing_or_invalid')
        n={'identity':identity(h),'field_handle':h,'parent_field_identity':None,'child_index':None,
           'graph_depth':None,'child_field_count':count,'child_field_ids':children,
           'child_resolution_status':'unresolved','object_reference_count':rc,'object_reference_ids':refs,
           'evaluator_id':one(block,'Node.Evaluator'),'raw_field_code':code,'field_code_status':cs,
           'raw_node_record':block,'raw_evaluation_value':one(block,'Node.EvaluationRaw'),
           'evaluation_status':'unsupported','child_index_references':[],
           'provenance':deepcopy(provenance),'unresolved_reasons':errors}
        nodes[h]=n;out['nodes'].append(n)
        for ref in refs:
            out['object_references'].append({'source_field_identity':identity(h),
                'target_identity':{'project_id':carrier.get('project_id'),'drawing_ref':carrier.get('drawing_ref'),
                 'snapshot_id':carrier.get('snapshot_id'),'handle':ref,'parent_path':None},
                'source':'FIELD DXF97/331','identity_status':'partial'})
        reasons.extend(h+':'+e for e in errors)
    seen=set()
    def visit(h,parent,index,depth,ancestors):
        if depth>MAX_DEPTH:reasons.append('depth_limit');return
        if h in ancestors:reasons.append('cycle:'+str(h));return
        if h not in nodes:reasons.append('missing_child_or_root:'+str(h));return
        if h in seen:reasons.append('multiple_parent_occurrence:'+str(h));return
        seen.add(h);n=nodes[h]
        n.update(parent_field_identity=identity(parent) if parent else None,child_index=index,graph_depth=depth)
        out['maximum_depth']=max(out['maximum_depth'],depth)
        for i,ch in enumerate(n['child_field_ids']):
            out['edges'].append({'parent_field_identity':identity(h),'child_field_identity':identity(ch),'child_index':i})
            visit(ch,h,i,depth+1,ancestors|{h})
        n['child_resolution_status']='resolved' if not n['unresolved_reasons'] and all(c in seen for c in n['child_field_ids']) else 'partial'
        for m in re.finditer(r'\\_FldIdx\s+(\d+)',n['raw_field_code'] or ''):
            idx=int(m[1]);ids=n['child_field_ids']
            ok=n['child_resolution_status']=='resolved' and idx<len(ids) and ids[idx] in nodes and not nodes[ids[idx]]['unresolved_reasons']
            n['child_index_references'].append({'index':idx,'status':'child_reference_resolved' if ok else 'unresolved',
                'child_field_identity':identity(ids[idx]) if ok else None})
            if not ok:reasons.append('unresolved_FldIdx:'+h+':'+str(idx))
    visit(root,None,None,0,set())
    if set(nodes)!=seen:reasons.append('unreachable_nodes')
    if not reasons and nodes:out.update(graph_status='complete',graph_complete=True)
    else:
        out['graph_status']='partial' if nodes else 'unresolved'
        # Never present a locally resolved child token as complete when the graph is unsafe.
        for n in out['nodes']:
            n['child_resolution_status']='partial'
            for ref in n['child_index_references']:ref['status']='unresolved'
    return out
