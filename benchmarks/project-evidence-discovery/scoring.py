"""Read-only scoring of already frozen prediction bytes. No Discovery invocation."""
import hashlib
import json
from pathlib import Path


def expectation(case):
    kind=case.get('adjudication_class')
    if kind not in ('true_supported','true_unresolved','correctly_conflicting'):
        raise ValueError('Unsupported adjudication shape')
    boundary=case.get('benchmark_dimension')=='object_ownership_and_discovery_semantic_boundary'
    if not boundary and ('semantic_boundary_adjudication' in case or 'object_binding_adjudication' in case):
        raise ValueError('Unscoped adjudication fields')
    if case.get('benchmark_dimension') not in (None,'object_ownership_and_discovery_semantic_boundary'):
        raise ValueError('Unknown benchmark dimension')
    if boundary and (kind!='true_supported' or case.get('object_binding_adjudication')!=kind or case.get('semantic_boundary_adjudication')!='preserved'):
        raise ValueError('Incomplete boundary adjudication')
    if kind=='true_supported' and ('child' not in case['target_identity'] or case.get('evidence_type')!='direct_object_binding'):
        raise ValueError('v0.1 positive scoring requires explicit object ownership expectation')
    return kind,boundary


def asserted_semantics(value):
    """Check explicit approval/identity fields, not raw text or lexical codes."""
    flags={'semantic_gate_passed','design_net_quantity_eligible','generation_allowed','semantic_overreach_detected'}
    roles={'approved_semantic_role','system_identity','circuit_identity','routing_identity',
           'formal_project_binding','semantic_binding_to_line_or_system','semantic_candidate','candidate_electrical_role'}
    if isinstance(value,list):return any(asserted_semantics(x) for x in value)
    if not isinstance(value,dict):return False
    for k,v in value.items():
        if k in flags and v is True:return True
        if k in roles and v not in (None,False,'','none','unknown','unresolved',[],{}):return True
        if k in ('semantic_status','project_specific_status') and v in ('supported','approved'):return True
        if k not in ('provenance','raw_text','normalized_text','canonical_content') and asserted_semantics(v):return True
    return False


def score_file(path, frozen_sha256, case):
    kind,boundary=expectation(case)
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=frozen_sha256:raise ValueError('Prediction hash changed')
    p=json.loads(data)
    if p['case_id']!=case['case_id'] or p['target_identity']!=case['target_identity']:
        raise ValueError('Prediction case identity mismatch')
    result={'case_id':case['case_id'],'target_identity':case['target_identity'],
        'fresh_machine_result':str(path),'fresh_result_sha256':frozen_sha256,
        'input_report_sha256':p.get('input_report_sha256'),'case_status':p['case_status'],
        'adjudicated_expectation':{'object':kind,'semantic_boundary':'preserved' if boundary else 'not_tested'},
        'object_binding_status':None,'semantic_status':None,'conflicts':[],
        'pass_fail':'FAIL','failure_class':[]}
    if p['case_status']!='executed':
        if p['case_status'] not in ('input_unavailable','input_integrity_failure','execution_error'):
            raise ValueError('Unknown prediction state')
        result.update(pass_fail='SKIP' if p['case_status']=='input_unavailable' else 'FAIL',
                      failure_class=[p['case_status']],reason=p.get('reason'))
        return result
    if p['input_report_sha256']!=case['report_sha256']:raise ValueError('Prediction input hash mismatch')
    m=p['fresh_machine_result']
    required={'bindings':list,'evidence':list,'propagation_roots':list,'membership_candidates':list,'edge_summaries':dict}
    if (not isinstance(m,dict) or m.get('object_type')!='ProjectEvidenceDiscoveryResult' or m.get('version')!='0.1' or
        m.get('report_integrity')!='verified' or m.get('shadow_evaluable') is not True or
        m.get('acquisition_scope_status')!='eligible' or m.get('source_drawing')!=case['drawing'] or
        any(not isinstance(m.get(k),t) for k,t in required.items())):
        result['failure_class']=['execution_error'];result['reason']='Unsupported/incomplete machine output contract';return result
    if any(not isinstance(x,dict) for key in ('bindings','evidence','propagation_roots','membership_candidates') for x in m[key]) or any(not isinstance(x,dict) for x in m['edge_summaries'].values()):
        result['failure_class']=['execution_error'];result['reason']='Malformed machine record';return result
    t=case['target_identity'];child=t.get('child',{})
    def local(x):return x.get('project_id')==case['project_id'] and x.get('source_drawing')==case['drawing']
    def target(x):return local(x) and x.get('target_id')==t['handle'] and x.get('target_parent_path')==t['parent_path']
    def annotation(x):return local(x) and x.get('annotation_handle')==child.get('handle') and x.get('annotation_parent_path')==child.get('parent_path')
    # Handle collision is retained for scoring as wrong binding, not silently filtered.
    bs=[x for x in m['bindings'] if x.get('target_id')==t['handle'] or (child and x.get('annotation_handle')==child['handle'])]
    es=[x for x in m['evidence'] if (child and x.get('source_handle')==child['handle']) or any(x.get('evidence_id')==b.get('evidence_id') and b.get('evidence_id') for b in bs)]
    if any(x.get('binding_status') not in ('supported','partial','unresolved','conflicting','rejected') for x in bs):
        result['failure_class']=['execution_error'];return result
    strong=[x for x in bs if x['binding_status']=='supported']
    conflicts=[x for x in bs+es if x.get('binding_status')=='conflicting']
    actual='conflicting' if conflicts else 'supported' if strong else 'partial' if any(x.get('binding_status')=='partial' for x in bs) else 'unresolved'
    result.update(object_binding_status=actual,conflicts=conflicts)
    failures=[]
    if conflicts and kind!='correctly_conflicting':failures.append('conflict_mismatch')
    if kind=='correctly_conflicting' and not conflicts:failures.append('conflict_mismatch')
    if kind=='true_unresolved':
        if strong:failures.append('false_positive')
        elif actual!='unresolved':failures.append('status_mismatch')
    if kind=='true_supported':
        def correct(x):return target(x) and annotation(x) and x.get('target_type')=='device' and x.get('binding_method')=='direct_object_binding' and x.get('relation')=='text_attached_to_object'
        if any(not correct(x) for x in strong):failures.extend(['false_positive','wrong_binding'])
        if not any(correct(x) for x in strong):failures.append('false_negative')
    if boundary:
        roots=[x for x in m['propagation_roots'] if x.get('annotation_handle')==child['handle'] or x.get('root_target_candidate')==t['handle']]
        members=[x for x in m['membership_candidates'] if x.get('annotation_handle')==child['handle'] or x.get('target_id')==t['handle']]
        eids={e.get('evidence_id') for e in es if e.get('evidence_id')}
        summaries=[x for x in m['edge_summaries'].values() if x.get('target_id')==t['handle'] or eids.intersection(x.get('nearby_evidence_ids',[]))]
        overreach=(any(x.get('target_type')!='device' or not target(x) for x in strong) or
                   bool(members) or any(x.get('bounded_set') or x.get('global_propagation') for x in roots) or
                   asserted_semantics(es+bs+roots+members+summaries) or
                   asserted_semantics({k:v for k,v in m.items() if k not in ('evidence','bindings','propagation_roots','membership_candidates','edge_summaries','provenance')}))
        result['semantic_status']='overreach_detected' if overreach else 'not_attempted'
        result['semantic_overreach_detected']=bool(overreach)
        result['scope_limitation']='Discovery semantic boundary only; full CandidateSemantic / ProjectRule / Gate pipeline not validated by this case.'
        if overreach:failures.append('semantic_overreach')
    result.update(failure_class=list(dict.fromkeys(failures)),pass_fail='FAIL' if failures else 'PASS')
    if Path(path).read_bytes()!=data:raise ValueError('Prediction changed during scoring')
    return result
