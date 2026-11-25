"""Typed candidate resolution. Source extraction is unchanged v1 code."""
from copy import deepcopy
import re
from references import scan as scan_v1
from registry import content_hash
from registry_v2 import migrate_v1, legacy_view, lookup as registry_lookup

VERSION=2
TARGET_KINDS=['drawing_instance','layout_instance']
ROLE_MAP={
    'drawing_number_reference':['drawing_number_candidate'],
    'drawing_title_reference':['drawing_title_candidate'],
    'cross_sheet_text_reference':['source_filename','filename_stem'],
    'sheet_number_reference_candidate':['sheet_number_candidate'],
}
WEAK_ROLES=['drawing_number_candidate','drawing_title_candidate','sheet_number_candidate',
            'sheet_title_candidate','source_filename','filename_stem']
SOURCE_FIELDS=('reference_type','raw_reference_text','reference_span','occurrence_index','identifier_index',
    'identifier_raw','identifier_normalized','normalization_status','target_identifier_status',
    'reference_id','project_id','source_drawing_instance_id','source_carrier_identity','source_subelement_identity',
    'carrier_type','source_text','raw_serialized_text','owner_insert_identity','source_relations',
    'reference_extraction_status','provenance')


def validate_registry(registry):
    if type(registry.get('registry_version')) is not int or registry['registry_version']!=2:
        raise ValueError('Registry v2 required; v1 is not silently migrated')
    old=legacy_view(registry)
    if migrate_v1(old)!=registry:raise ValueError('inconsistent Registry v2')
    return old


def identity_supported(t):
    """Pure policy for a future independently authorized target; no inference."""
    s=t.get('identity_support')
    if t.get('logical_identity_status')!='supported' or not isinstance(s,dict):return False
    if t.get('target_kind')=='layout_instance' and t.get('sheet_identity_status')!='supported':return False
    expected={k:t.get(k) for k in ('project_id','target_kind','target_id','drawing_instance_id','layout_instance_id')}
    if s.get('status')!='supported' or s.get('independent') is not True or s.get('target_identity')!=expected:return False
    if s.get('approved_alias_role')!=t.get('matched_alias_role') or s.get('approved_alias_value')!=t.get('matched_alias_value'):return False
    p=s.get('provenance')
    return isinstance(p,list) and bool(p) and all(isinstance(x,dict) and isinstance(x.get('source_id'),str)
        and bool(x['source_id'].strip()) and isinstance(x.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',x['sha256']) for x in p)


def decide_resolution(source_status,lookup_status,targets,weak_role):
    if source_status=='conflicting' or lookup_status=='conflicting' or any(t.get('logical_identity_status')=='conflicting' for t in targets):
        return 'conflicting',['source_or_target_identity_conflict']
    if source_status!='supported':return 'unresolved',['source_reference_not_supported']
    if lookup_status not in ('unique_registry_candidate','ambiguous'):return 'unresolved',['lookup_not_resolved']
    if not targets:return 'unresolved',['no_identifier_or_target']
    if len(targets)>1 or lookup_status=='ambiguous':return 'ambiguous',['multiple_typed_targets; no automatic selection']
    if not weak_role and identity_supported(targets[0]):return 'supported',['unique_independently_supported_target']
    return 'candidate',['unique_target_is_not_approved_identity']


def _targets(registry,match):
    drawings={d['instance_id']:d for d in registry['drawing_instances']}
    layouts={l['layout_instance_id']:l for l in registry['layout_instances']}
    result=[]
    for m in match['matches']:
        kind,tid=m['target_kind'],m['target_id']
        if kind=='drawing_instance':
            obj=drawings[tid];did=tid;lid=None
            logical=obj['logical_identity_status'];sheet=obj['sheet_identity_status']
        elif kind=='layout_instance':
            obj=layouts[tid];did=obj['drawing_instance_id'];lid=tid
            logical=obj['logical_layout_identity_status'];sheet=obj['sheet_identity_status']
        else:raise ValueError('unsupported target kind')
        evidence=[deepcopy(a) for a in match['match_evidence'] if a['target_kind']==kind and a['target_id']==tid]
        # Do not choose one strongest alias when several observations match.
        values=sorted({a['value'] for a in evidence});roles=sorted({a['alias_role'] for a in evidence})
        statuses=sorted({a['evidence_status'] for a in evidence})
        result.append({'project_id':registry['project_id'],'target_kind':kind,'target_id':tid,
            'drawing_instance_id':did,'layout_instance_id':lid,
            'matched_alias_value':values[0] if len(values)==1 else values,
            'matched_alias_role':roles[0] if len(roles)==1 else roles,
            'identity_evidence_status':statuses[0] if len(statuses)==1 else statuses,
            'logical_identity_status':logical,'sheet_identity_status':sheet,
            'matched_alias_evidence':evidence,'identity_support':None,
            'provenance':deepcopy(obj['provenance'])})
    return result


def resolve_reference(registry,source,allowed_target_kinds=None):
    validate_registry(registry)
    if source.get('project_id')!=registry['project_id']:raise ValueError('foreign source project')
    kinds=TARGET_KINDS if allowed_target_kinds is None else allowed_target_kinds
    if not isinstance(kinds,list) or any(k not in TARGET_KINDS for k in kinds):raise ValueError('unsupported target-kind filter')
    kinds=sorted(set(kinds));typ=source['reference_type'];roles=ROLE_MAP.get(typ,WEAK_ROLES)
    weak=typ not in ROLE_MAP;q=source.get('identifier_normalized')
    if q is not None and (not isinstance(q,str) or not q.strip()):raise ValueError('invalid identifier')
    if q is None:match={'lookup_status':'not_attempted','matches':[],'match_evidence':[]}
    else:match=registry_lookup(registry,q,roles=roles,target_kinds=kinds)
    targets=_targets(registry,match)
    status,reasons=decide_resolution(source.get('reference_extraction_status'),match['lookup_status'],targets,weak)
    if q is None:reasons=['source_identifier_missing'] if status!='conflicting' else reasons
    elif not targets:reasons=['registry_zero_match_for_declared_roles_and_kinds'] if status!='conflicting' else reasons
    return {'reference_id':source['reference_id'],'registry_version':2,'lookup_query':q,
        'lookup_roles':roles.copy(),'lookup_target_kinds':kinds,'weak_source_role':weak,'fallbacks':[],
        'target_candidates':targets,'lookup_status':match['lookup_status'],'resolution_status':status,
        'resolution_reasons':reasons,'provenance':{'source':deepcopy(source.get('provenance',[])),
            'registry_content_hash':content_hash(registry)}}


def scan(registry,contexts):
    old=validate_registry(registry)
    # Only source extraction/identity validation uses v1. No v1 target matches are
    # used, and its historical implementation is untouched.
    source_view=deepcopy(old);source_view['aliases']=[];source_view['lookup_index']={}
    extracted=scan_v1(source_view,contexts)
    sources=[{k:deepcopy(r[k]) for k in SOURCE_FIELDS} for r in extracted['source_references']]
    resolutions=[resolve_reference(registry,r) for r in sources]
    groups={s:[r for r in resolutions if r['resolution_status']==s] for s in ('supported','candidate','ambiguous','unresolved','conflicting')}
    no_identifier=sum(s['identifier_normalized'] is None for s in sources)
    unmatched_titles=sum(s['reference_type']=='drawing_title_reference' and r['lookup_status']=='not_found' for s,r in zip(sources,resolutions))
    return {'version':VERSION,'ExplicitCrossSheetReferenceVersion':VERSION,'registry_version':2,
        'project_id':registry['project_id'],'source_references':sources,'resolutions':resolutions,
        'supported_links':groups['supported'],'candidate_links':groups['candidate'],'ambiguous_links':groups['ambiguous'],
        'unresolved_references':groups['unresolved'],'conflicts':groups['conflicting'],
        'source_conflict_evidence':extracted['conflicts'],'excluded_evidence':extracted['excluded_evidence'],
        'carrier_coverage':extracted['carrier_coverage'],'field_coverage':extracted['field_coverage'],
        'summary':{'source_reference_count':len(sources),
            'references_with_explicit_identifier':sum(s['identifier_normalized'] is not None and s['reference_type'] in ('drawing_number_reference','cross_sheet_text_reference','sheet_number_reference_candidate') for s in sources),
            'references_with_identifier_candidate':sum(s['identifier_normalized'] is not None for s in sources),
            'references_with_only_cue_or_title':sum(s['identifier_normalized'] is None or s['reference_type']=='drawing_title_reference' for s in sources),
            'drawing_target_hits':sum(any(t['target_kind']=='drawing_instance' for t in r['target_candidates']) for r in resolutions),
            'layout_target_hits':sum(any(t['target_kind']=='layout_instance' for t in r['target_candidates']) for r in resolutions),
            **{k:len(v) for k,v in groups.items()},'source_identifier_insufficient_count':no_identifier+unmatched_titles,
            'registry_zero_match_count':sum(r['lookup_status']=='not_found' for r in resolutions),
            'registry_multi_match_count':sum(len(r['target_candidates'])>1 for r in resolutions),
            'target_identity_unresolved_count':sum(r['resolution_status']=='candidate' for r in resolutions)},
        'provenance':{'sources':extracted['provenance'],'registry_content_hash':content_hash(registry)},
        'scope_limitation':'Typed reference resolution only; no engineering semantics or quantity; current Registry has no identity authority importer'}
