"""Lossless evidence projection. No extraction, lookup, identity inference or approval."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'explicit-cross-sheet-reference'),str(ROOT/'project-drawing-registry')]
from references_v2 import decide_resolution, SOURCE_FIELDS

VERSION=1
STATUSES=('supported','candidate','ambiguous','unresolved','conflicting')

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def digest(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def require(condition,reason):
    if not condition:raise ValueError(reason)

def text(value):return isinstance(value,str) and bool(value.strip())
def sha(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None

def provenance(value):
    require(isinstance(value,list) and bool(value),'missing provenance')
    require(all(isinstance(x,dict) and sha(x.get('sha256')) for x in value),'invalid provenance hash')

def indexed(items):
    require(isinstance(items,list),'expected records array')
    result={}
    for item in items:
        require(isinstance(item,dict) and text(item.get('reference_id')),'missing reference identity')
        key=item['reference_id']
        require(key not in result or result[key]==item,'contradictory duplicate reference identity')
        result[key]=item
    return result

def validate(document):
    require(isinstance(document,dict),'expected References v2 object')
    for key in ('version','ExplicitCrossSheetReferenceVersion','registry_version'):
        require(type(document.get(key)) is int and document[key]==2,'References v2 / Registry v2 required')
    project=document.get('project_id');require(text(project),'missing project')
    for key in ('source_conflict_evidence','excluded_evidence'):
        require(isinstance(document.get(key),list),'missing evidence collection: '+key)
    p=document.get('provenance');require(isinstance(p,dict) and sha(p.get('registry_content_hash')),'missing registry provenance')
    require(isinstance(p.get('sources'),list),'missing source inventory')
    inventory=set()
    for item in p['sources']:
        require(isinstance(item,dict) and text(item.get('source_drawing_instance_id')) and sha(item.get('report_sha256')),'invalid source inventory')
        inventory.add((item['source_drawing_instance_id'],item['report_sha256']))
    sources=indexed(document.get('source_references'));resolutions=indexed(document.get('resolutions'))
    require(sources.keys()==resolutions.keys(),'missing or orphan resolution')
    for rid,s in sources.items():
        require(all(k in s for k in SOURCE_FIELDS),'incomplete source contract')
        require(s['project_id']==project and text(s['source_drawing_instance_id']),'foreign source identity')
        c=s['source_carrier_identity']
        require(isinstance(c,dict) and c.get('project_id')==project and all(text(c.get(k)) for k in ('drawing_ref','handle','snapshot_id')),'invalid carrier identity')
        require(isinstance(c.get('parent_path'),list) and all(text(x) for x in c['parent_path']),'missing parent_path')
        require((s['source_drawing_instance_id'],c['snapshot_id']) in inventory,'source snapshot not in inventory')
        provenance(s['provenance'])
        require(any(x['sha256']==c['snapshot_id'] for x in s['provenance']),'carrier snapshot provenance mismatch')
        r=resolutions[rid]
        require(type(r.get('registry_version')) is int and r['registry_version']==2,'invalid resolution version')
        require(r.get('provenance')=={'source':s['provenance'],'registry_content_hash':p['registry_content_hash']},'resolution provenance mismatch')
        require(r.get('resolution_status') in STATUSES,'unknown resolution status')
        require(isinstance(r.get('resolution_reasons'),list) and bool(r['resolution_reasons']) and all(text(x) for x in r['resolution_reasons']),'missing resolution reasons')
        require(type(r.get('weak_source_role')) is bool and r.get('fallbacks')==[],'invalid lookup contract')
        require(isinstance(r.get('lookup_roles'),list) and bool(r['lookup_roles']) and all(text(x) for x in r['lookup_roles']),'invalid lookup roles')
        require(isinstance(r.get('lookup_target_kinds'),list) and all(x in ('drawing_instance','layout_instance') for x in r['lookup_target_kinds']),'invalid lookup kinds')
        q=s['identifier_normalized'];require(q is None or text(q),'invalid identifier')
        require(r.get('lookup_query')==q,'query/source identifier mismatch')
        targets=r.get('target_candidates');require(isinstance(targets,list),'missing target candidates')
        seen=set()
        for t in targets:
            require(isinstance(t,dict) and t.get('project_id')==project,'foreign target project')
            kind=t.get('target_kind');tid=t.get('target_id');did=t.get('drawing_instance_id');lid=t.get('layout_instance_id')
            require(kind in r['lookup_target_kinds'] and text(tid) and text(did),'unsupported target kind or missing identity')
            require((kind=='drawing_instance' and tid==did and lid is None) or (kind=='layout_instance' and tid==lid and tid!=did),'invalid typed identity; no flattening')
            require((kind,tid) not in seen,'duplicate target identity');seen.add((kind,tid))
            require(all(k in t for k in ('matched_alias_role','matched_alias_value','matched_alias_evidence','logical_identity_status','sheet_identity_status')),'missing typed target evidence')
            provenance(t.get('provenance'))
        lookup=r.get('lookup_status')
        require(lookup in ('not_attempted','not_found','unique_registry_candidate','ambiguous','conflicting'),'unknown lookup status')
        require((q is None and lookup=='not_attempted' and not targets) or (q is not None and lookup!='not_attempted'),'identifier/lookup inconsistency')
        require(lookup!='not_found' or not targets,'zero match with candidates')
        require(lookup!='unique_registry_candidate' or len(targets)==1,'unique match count mismatch')
        require(lookup!='ambiguous' or len(targets)>1,'ambiguity count mismatch')
        status,_=decide_resolution(s['reference_extraction_status'],lookup,targets,r['weak_source_role'])
        require(status==r['resolution_status'],'upstream status contract inconsistency')
    return project,sources,resolutions

def build_graph(document,source_sha256):
    require(sha(source_sha256),'invalid source artifact SHA-256')
    project,sources,resolutions=validate(document)
    nodes={};edges=[];records=[]
    def node(kind,identity):
        nid=digest([VERSION,project,kind,identity])
        nodes[nid]={'node_id':nid,'kind':kind,'project_id':project,'identity':deepcopy(identity)}
        return nid
    def edge(relation,a,b,rid,evidence=None):
        item={'relation':relation,'from_node':a,'to_node':b,'reference_id':rid}
        if evidence is not None:item['evidence']=deepcopy(evidence)
        item['edge_id']=digest(item);edges.append(item)
    counts={k:0 for k in STATUSES};missing=misses=0
    for rid in sorted(sources):
        s=sources[rid];r=resolutions[rid]
        dn=node('drawing_instance',{'drawing_instance_id':s['source_drawing_instance_id']})
        rn=node('source_reference',{'reference_id':rid})
        edge('contains_source_reference',dn,rn,rid)
        ident=None
        if s['identifier_normalized'] is not None:
            ident=node('source_identifier',{'reference_id':rid,'raw':s['identifier_raw'],'normalized':s['identifier_normalized']})
            edge('observed_identifier',rn,ident,rid)
        else:missing+=1
        if r['lookup_status']=='not_found':misses+=1
        candidates=[]
        for t in r['target_candidates']:
            identity={'drawing_instance_id':t['drawing_instance_id']}
            if t['target_kind']=='layout_instance':identity['layout_instance_id']=t['layout_instance_id']
            tn=node(t['target_kind'],identity);candidates.append(tn)
            if t['target_kind']=='layout_instance':
                parent=node('drawing_instance',{'drawing_instance_id':t['drawing_instance_id']})
                edge('reported_layout_parent',tn,parent,rid)
            edge('reported_target_candidate',rn,tn,rid,t)
        counts[r['resolution_status']]+=1
        records.append({'reference_id':rid,'reference_node_id':rn,'identifier_node_id':ident,
            'target_node_ids':sorted(candidates),'source_reference':deepcopy(s),'resolution':deepcopy(r),
            'resolution_status':r['resolution_status'],'unresolved_reasons':deepcopy(r['resolution_reasons']) if r['resolution_status']=='unresolved' else [],
            'diagnostic': 'identifier_missing' if ident is None else 'registry_exact_match_failed' if r['lookup_status']=='not_found' else 'upstream_resolution_recorded'})
    graph={'CrossSheetEvidenceGraphVersion':VERSION,'project_id':project,'source_contract_version':2,'registry_version':2,
        'source_artifact_sha256':source_sha256,'formal_authorization':False,
        'nodes':sorted(nodes.values(),key=lambda n:n['node_id']),'edges':sorted(edges,key=lambda e:e['edge_id']),
        'records':records,'source_conflict_evidence':deepcopy(document['source_conflict_evidence']),
        'excluded_evidence':deepcopy(document['excluded_evidence']),'provenance':deepcopy(document['provenance']),
        'summary':{'reference_count':len(records),**counts,'identifier_missing':missing,'registry_exact_match_failed':misses,
            'drawing_target_hits':sum(any(t['target_kind']=='drawing_instance' for t in r['target_candidates']) for r in resolutions.values()),
            'layout_target_hits':sum(any(t['target_kind']=='layout_instance' for t in r['target_candidates']) for r in resolutions.values())},
        'scope_limitation':'Evidence recording only; not identity approval, engineering semantics or quantity authorization'}
    graph['content_hash']=digest(graph)
    return graph
