"""Layout-qualified directory, candidate lookup only. No identity approval."""
from copy import deepcopy
from collections import Counter
import re

from registry import build_registry as build_v1, content_hash, key, required

VERSION = 2
ROLES = {'source_filename', 'filename_stem', 'drawing_number_candidate',
         'drawing_title_candidate', 'sheet_number_candidate', 'sheet_title_candidate',
         'layout_name', 'revision_candidate', 'unknown_identifier_candidate'}
KINDS = {'drawing_instance', 'layout_instance', 'sheet_identity_candidate'}
SHEET_ROLES = {'sheet_number_candidate', 'sheet_title_candidate'}
NUMBER_TITLE = {'drawing_number_candidate','drawing_title_candidate',*SHEET_ROLES,'unknown_identifier_candidate'}


def unique(items):
    return [v for _,v in sorted({content_hash(x):x for x in items}.items())]


def hash_value(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def provenance(records, source_type, sha=None):
    if not isinstance(records,list) or not records:
        raise ValueError('missing provenance')
    found={p.get('sha256') for p in records if isinstance(p,dict) and p.get('source_type')==source_type}
    if not found or any(not hash_value(h) for h in found) or (sha is not None and found!={sha}):
        raise ValueError('unbound source hash')
    return found


def role(kind):
    if kind.startswith('revision_'):return 'revision_candidate'
    if kind.startswith('unresolved_'):return 'unknown_identifier_candidate'
    if kind not in ROLES:raise ValueError('unsupported alias role')
    return kind


def migrate_v1(old):
    if type(old.get('registry_version')) is not int or old['registry_version']!=1:
        raise ValueError('Registry v1 required')
    project=required(old.get('project_id'),'project_id')
    drawings={};layouts={};aliases=[];coverage=[];conflicts=[];sheets=[]
    for d in old.get('drawing_instances',[]):
        basis={k:d.get(k) for k in ('project_id','drawing_ref','source_dwg_sha256','report_sha256')}
        iid=d.get('instance_id')
        if basis['project_id']!=project or not isinstance(basis['drawing_ref'],str) or not basis['drawing_ref'] or not hash_value(basis['report_sha256']) or content_hash(basis)!=iid:
            raise ValueError('invalid drawing identity')
        provenance(d.get('provenance'),'report_bytes',d['report_sha256'])
        if iid in drawings:
            if drawings[iid]!=d:raise ValueError('conflicting drawing observation')
            continue
        drawings[iid]=deepcopy(d)
        e=d.get('drawing_sheet_identity_evidence')
        if e is None:
            coverage.append({'drawing_instance_id':iid,'status':'not_supplied','reason':'no layout evidence supplied; inventory unknown'})
            continue
        if type(e.get('DrawingSheetIdentityEvidenceVersion')) is not int or e['DrawingSheetIdentityEvidenceVersion']!=1 or e.get('project_id')!=project or e.get('drawing_instance_id')!=iid:
            raise ValueError('foreign or incompatible identity evidence')
        hashes=provenance(e.get('provenance'),'layout_report_bytes')
        if len(hashes)!=1:raise ValueError('ambiguous layout snapshot')
        sha=next(iter(hashes));native_to_new={}
        if not isinstance(e.get('layouts'),list) or not e['layouts']:raise ValueError('empty supplied layout inventory')
        for l in unique(e['layouts']):
            native=l.get('layout_source_identity',{})
            if (l.get('project_id')!=project or l.get('drawing_instance_id')!=iid
                or l.get('space_type') not in ('ModelSpace','PaperSpace')
                or any(not isinstance(native.get(k),str) or not re.fullmatch('[0-9A-Fa-f]+',native[k]) for k in ('handle','block_handle'))):
                raise ValueError('foreign/malformed layout identity')
            name=required(l.get('layout_name'),'layout name')
            expected=content_hash([project,iid,name,native['handle'],native['block_handle']])
            if l.get('layout_identity')!=expected:raise ValueError('layout identity mismatch')
            provenance(l.get('provenance'),'layout_report_bytes',sha)
            lid=content_hash({'project_id':project,'drawing_instance_id':iid,'layout_name':name,'layout_source_identity':native})
            native_to_new[expected]=lid
            obj={'layout_instance_id':lid,'project_id':project,'drawing_instance_id':iid,'drawing_ref':d['drawing_ref'],
                'layout_name':name,'space_type':l['space_type'],'layout_order':l.get('layout_order'),
                'layout_source_identity':deepcopy(native),'source_layout_identity':expected,
                'layout_report_identity':{'drawing_ref':d['drawing_ref'],'report_version':'2.9-layout-identity-v1','snapshot_id':sha},
                'layout_report_sha256':sha,'layout_acquisition_status':l.get('layout_acquisition_status'),
                'paperspace_entity_count':l.get('entity_count') if l['space_type']=='PaperSpace' else None,
                'identity_candidates':[],'revision_candidates':[],
                'sheet_identity_status':'not_applicable' if l['space_type']=='ModelSpace' else 'unresolved',
                'logical_layout_identity_status':'unresolved','provenance':deepcopy(l['provenance'])}
            if obj['layout_acquisition_status'] not in ('read','unavailable') or (obj['paperspace_entity_count'] is not None and (type(obj['paperspace_entity_count']) is not int or obj['paperspace_entity_count']<0)):
                raise ValueError('invalid layout acquisition state/count')
            if lid in layouts and layouts[lid]!=obj:raise ValueError('conflicting native layout observation')
            layouts[lid]=obj
            aliases.append({'value':name,'normalized_value':key(name),'alias_role':'layout_name',
                'target_kind':'layout_instance','target_id':lid,'evidence_status':'observed',
                'evidence_strength':'native_layout_name_only','source_layout_identity':expected,
                'source_carrier_identity':native,'provenance':deepcopy(l['provenance'])})
        coverage.append({'drawing_instance_id':iid,'status':'supplied','layout_report_sha256':sha})
        for c in unique(e.get('candidates',[])):
            lid=native_to_new.get(c.get('layout_identity'));i=c.get('carrier_identity',{})
            if lid is None:raise ValueError('candidate layout missing')
            l=layouts[lid]
            if any(i.get(k)!=v for k,v in {'project_id':project,'drawing_instance_id':iid,'drawing_ref':d['drawing_ref'],'snapshot_id':sha,'layout_identity':c['layout_identity']}.items()):
                raise ValueError('foreign candidate identity')
            if not isinstance(i.get('parent_path'),list) or not all(isinstance(x,str) and x for x in i['parent_path']) or not isinstance(i.get('handle'),str) or not i['handle']:
                raise ValueError('incomplete carrier identity')
            provenance(c.get('provenance'),'layout_report_bytes',sha)
            if c.get('status')!='candidate':raise ValueError('unsupported candidate approval claim')
            if l['space_type']!='PaperSpace' or l['layout_acquisition_status']!='read':
                raise ValueError('identity candidate outside acquired PaperSpace')
            value=required(c.get('value'),'candidate value');r=role(c['kind'])
            obs={'value':value,'normalized_value':key(value),'alias_role':r,'source_kind':c['kind'],
                'identifier_role':c.get('identifier_role','unresolved'),'evidence_status':'candidate',
                'evidence_strength':required(c.get('evidence_strength'),'evidence strength'),
                'source_carrier_identity':deepcopy(i),'source_attribute_tag':c.get('tag'),
                'source_field_graph':deepcopy(c.get('field_graph')),'source_layout_identity':c['layout_identity'],
                'provenance':deepcopy(c['provenance'])}
            obs['candidate_id']=content_hash([lid,obs])
            l['revision_candidates' if r=='revision_candidate' else 'identity_candidates'].append(obs)
    if not drawings:raise ValueError('no drawing instances')
    for a in old.get('aliases',[]):
        d=drawings.get(a.get('instance_id'))
        if d is None:raise ValueError('foreign drawing alias')
        provenance(a.get('provenance'),'report_bytes',d['report_sha256'])
        src=a.get('source_identity')
        if src is not None:
            if not isinstance(src,dict) or any(k in src and src[k]!=v for k,v in
                {'project_id':project,'snapshot_id':d['report_sha256'],'drawing_ref':d['drawing_ref']}.items()):
                raise ValueError('foreign drawing alias source identity')
        if a.get('status') not in ('partial','candidate','observed'):raise ValueError('unsupported drawing alias status')
        # Old flat layout attachments are retained in the legacy view only. v2
        # reconstructs their true Layout targets instead of duplicating the role.
        if a.get('source_type')=='layout_title_block':continue
        value=required(a.get('value'),'alias');r=role(a['kind'])
        aliases.append({'value':value,'normalized_value':key(value),'alias_role':r,
            'target_kind':'drawing_instance','target_id':d['instance_id'],'evidence_status':a['status'],
            'evidence_strength':a.get('source_type','v1_drawing_alias_candidate'),
            'source_carrier_identity':deepcopy(a.get('source_identity')),'provenance':deepcopy(a['provenance'])})
    for lid,l in sorted(layouts.items()):
        l['identity_candidates']=unique(l['identity_candidates']);l['revision_candidates']=unique(l['revision_candidates'])
        cs=l['identity_candidates'];by_role={}
        for c in cs:by_role.setdefault((c['alias_role'],c['identifier_role']),set()).add(c['value'])
        bad=[{'role':r,'identifier_role':ir,'values':sorted(v)} for (r,ir),v in sorted(by_role.items()) if len(v)>1]
        if bad:
            l['logical_layout_identity_status']='conflicting'
            conflicts.append({'layout_instance_id':lid,'reason':'contradictory_identity_values','roles':bad,'evidence':cs})
        elif cs:l['logical_layout_identity_status']='candidate'
        sheet_cs=[c for c in cs if c['alias_role'] in SHEET_ROLES]
        if sheet_cs:
            l['sheet_identity_status']='conflicting' if any(b['role'] in SHEET_ROLES for b in bad) else 'candidate'
            sid=content_hash([lid,'sheet_identity_candidate'])
            sheets.append({'sheet_candidate_id':sid,'layout_instance_id':lid,'drawing_instance_id':l['drawing_instance_id'],
                'project_id':project,'status':l['sheet_identity_status'],'evidence':sheet_cs,'approved':False})
        for c in cs+l['revision_candidates']:
            a=dict(deepcopy(c),target_kind='layout_instance',target_id=lid)
            aliases.append(a)
            if c['alias_role'] in SHEET_ROLES:
                aliases.append(dict(deepcopy(c),target_kind='sheet_identity_candidate',target_id=content_hash([lid,'sheet_identity_candidate'])))
    aliases=unique(aliases);index={}
    for a in aliases:index.setdefault(a['normalized_value'],set()).add((a['target_kind'],a['target_id']))
    ambiguous=[{'query_key':k,'targets':[{'target_kind':t,'target_id':i} for t,i in sorted(v)],'status':'ambiguous'} for k,v in sorted(index.items()) if len(v)>1]
    ls=[layouts[k] for k in sorted(layouts)]
    return {'registry_version':VERSION,'ProjectDrawingRegistryVersion':VERSION,'project_id':project,
        'drawing_instances':[drawings[k] for k in sorted(drawings)],'layout_instances':ls,
        'sheet_identity_candidates':sheets,'aliases':aliases,'drawing_layout_coverage':unique(coverage),
        'ambiguities':ambiguous,'conflicts':conflicts,
        'source_registry_v1':deepcopy(old),'source_registry_v1_hash':content_hash(old),
        'summary':{'drawing_instance_count':len(drawings),'layout_instance_count':len(ls),
            'paperspace_layout_count':sum(l['space_type']=='PaperSpace' for l in ls),
            'layout_identity_candidate_count':sum(len(l['identity_candidates']) for l in ls),
            'sheet_identity_supported_count':0,
            'sheet_identity_unresolved_count':sum(l['space_type']=='PaperSpace' and l['sheet_identity_status']=='unresolved' for l in ls),
            'ambiguous_alias_count':len(ambiguous),'conflict_count':len(conflicts),
            'drawing_without_layout_evidence_count':sum(c['status']=='not_supplied' for c in coverage),
            'layout_without_identity_evidence_count':sum(not l['identity_candidates'] for l in ls),
            'report_version_distribution':dict(sorted(Counter(d.get('report_version','unknown') for d in drawings.values()).items()))},
        'provenance':{'source_registry_content_hash':content_hash(old),'authority':'candidate evidence only; no Sheet approval'}}


def build_registry(project_id,inputs):
    return migrate_v1(build_v1(project_id,inputs))


def legacy_view(registry):
    if type(registry.get('registry_version')) is not int or registry['registry_version']!=2:raise ValueError('Registry v2 required')
    old=registry.get('source_registry_v1')
    if not isinstance(old,dict) or content_hash(old)!=registry.get('source_registry_v1_hash') or old.get('project_id')!=registry.get('project_id'):
        raise ValueError('invalid legacy source')
    return deepcopy(old)


def lookup(registry,value,roles=None,target_kinds=None):
    required(value,'query')
    # Rebuild from retained source to prevent a stale/tampered index from selecting
    # a target. This is consistency validation, not source authentication.
    canonical=migrate_v1(legacy_view(registry))
    if registry!=canonical:raise ValueError('inconsistent v2 registry')
    for values,allowed in ((roles,ROLES),(target_kinds,KINDS)):
        if values is not None and (not isinstance(values,list) or any(not isinstance(v,str) or v not in allowed for v in values)):
            raise ValueError('invalid role/target-kind filter')
    evidence=[a for a in registry['aliases'] if a['normalized_value']==key(value)
              and (roles is None or a['alias_role'] in roles) and (target_kinds is None or a['target_kind'] in target_kinds)]
    targets=sorted({(a['target_kind'],a['target_id']) for a in evidence})
    bad={c['layout_instance_id'] for c in registry['conflicts']}
    sheet_bad={s['sheet_candidate_id'] for s in registry['sheet_identity_candidates'] if s['layout_instance_id'] in bad}
    conflict=any((t=='layout_instance' and i in bad) or (t=='sheet_identity_candidate' and i in sheet_bad) for t,i in targets)
    status='not_found' if not targets else 'conflicting' if conflict else 'ambiguous' if len(targets)>1 else 'unique_registry_candidate'
    return {'query':value,'roles':roles,'target_kinds':target_kinds,'lookup_status':status,
        'matches':[{'target_kind':t,'target_id':i} for t,i in targets],'match_count':len(targets),
        'match_evidence':evidence,'logical_identity_approved':False,'sheet_identity_approved':False}
