"""Candidate + reviewed object-bound evidence -> project semantic decision only."""
from copy import deepcopy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_identity import scope_identity, identity_record
from evidence import DIRECT_STRENGTHS, WEAK_STRENGTHS, DIRECT_TYPES, WEAK_TYPES


def evaluate_semantics(candidate, bundle, context):
    edge=candidate.get('edge_handle')
    result={'model_type':'ProjectSpecificSemanticDecision','resolver_version':'0.1','edge_handle':edge,
            'segment_id':candidate.get('segment_id'),'candidate_role':candidate.get('candidate_role','unknown'),
            'candidate_confidence':candidate.get('candidate_confidence','unknown'),
            'project_specific_status':'unresolved','approved_semantic_role':None,
            'semantic_gate_passed':False,'design_net_quantity_eligible':False,
            'quantity_eligibility_status':'not_evaluated','quantity_generated':False,
            'eligibility_meaning':'semantic permission to enter QuantityEligibilityResolver only',
            'accepted_evidence':[],'rejected_evidence':[],'conflicting_evidence':[],
            'limiting_evidence':[],'evidence_binding_type':[],'binding_targets':[],
            'candidate_overridden':False,'override_reason':None,
            'provenance':{'candidate':deepcopy(candidate),'project_evidence':deepcopy(bundle.get('provenance',[])),
                          'context':deepcopy(context)},
            'assumptions':['Reviewed object bindings are supplied by the project evidence author',
                           'All admitted direct evidence is peer evidence; no inferred source hierarchy',
                           'Rejected semantic claim does not reject geometry or indirect electrical relationships',
                           'No geometry, roles, candidate rules or quantities recomputed']}
    try:
        identity = scope_identity(candidate)
        if scope_identity(context) != identity:
            raise ValueError('Candidate/context instance identity mismatch')
        result['object_identity'] = identity_record(candidate)
    except ValueError as exc:
        result['limiting_evidence'].append(str(exc));return result
    records=bundle.get('evidence',[]);bindings=bundle.get('bindings',[])
    def reject(e,reason):result['rejected_evidence'].append({'evidence':deepcopy(e),'reason':reason})
    ids=[e.get('evidence_id') for e in records];bids=[b.get('binding_id') for b in bindings]
    if not edge or None in ids or None in bids or len(set(ids))!=len(ids) or len(set(bids))!=len(bids):
        result['limiting_evidence'].append('missing identity or duplicate evidence/binding ids');return result
    if any(not context.get(k) or context[k]!=bundle.get(k) for k in ('project_id','drawing_ref')):
        result['limiting_evidence'].append('project/drawing context missing or mismatched');return result
    by_id={b['binding_id']:b for b in bindings}
    direct=[];pending=[];weak=[]
    for e in records:
        typ=e.get('evidence_type');strength=e.get('evidence_strength')
        if typ in WEAK_TYPES or strength in WEAK_STRENGTHS:
            weak.append(e);reject(e,'non-direct evidence cannot authorize project semantics');continue
        if typ not in DIRECT_TYPES or strength not in DIRECT_TYPES[typ]:
            reject(e,'unrecognized evidence type or incompatible strength');continue
        b=by_id.get(e.get('binding_id'))
        try:
            bound_identity = scope_identity(b)
        except ValueError:
            reject(e,'incomplete instance identity');pending.append(e);continue
        if bound_identity != identity:
            reject(e,'foreign full instance/scope binding');continue
        if 'object_identity' in e:
            try:
                if scope_identity(e['object_identity']) != identity:
                    raise ValueError('Evidence identity mismatch')
            except ValueError:
                reject(e,'evidence instance identity inconsistent');pending.append(e);continue
        # Applicable unresolved direct evidence must not disappear behind a good claim.
        if (b.get('review_status')!='reviewed' or not b.get('provenance') or not e.get('provenance') or
                e['evidence_id'] not in b.get('evidence_ids',[])):
            reject(e,'binding review/provenance incomplete');pending.append(e);continue
        result['evidence_binding_type'].append(strength)
        result['binding_targets'].append(deepcopy(b))
        if e.get('status')!='supported' or e.get('assertion') not in ('affirm','deny') or e.get('semantic_role') in (None,'','unknown','unresolved'):
            pending.append(e);reject(e,'direct evidence unresolved or not supported');continue
        direct.append(e)
        accepted=deepcopy(e);accepted['object_identity']=identity_record(b)
        result['accepted_evidence'].append(accepted)
    positive=[e for e in direct if e['assertion']=='affirm']
    negative=[e for e in direct if e['assertion']=='deny']
    roles={e['semantic_role'] for e in positive}
    denied={e['semantic_role'] for e in negative}
    if len(roles)>1 or roles & denied or any(e.get('status')=='conflicting' for e in pending):
        result['project_specific_status']='conflicting'
        result['conflicting_evidence']=deepcopy(direct+pending)
        return result
    if pending:
        result['project_specific_status']='partial' if positive else 'unresolved'
        result['limiting_evidence'].append({'unresolved_direct_evidence':deepcopy(pending)})
        return result
    if positive:
        approved=next(iter(roles));result['approved_semantic_role']=approved
        result['project_specific_status']='supported'
        result['semantic_gate_passed']=True;result['design_net_quantity_eligible']=True
        old=result['candidate_role']
        if old not in ('unknown','unresolved',None,'') and old!=approved:
            result['candidate_overridden']=True
            result['override_reason']='Direct project evidence takes precedence over candidate semantics'
            result['conflicting_evidence'].append({'kind':'candidate_vs_direct','candidate_role':old,'approved_semantic_role':approved})
        return result
    if result['candidate_role'] in denied:
        result['project_specific_status']='rejected';return result
    if weak or result['candidate_role'] not in ('unknown','unresolved',None,''):
        result['project_specific_status']='partial'
    result['limiting_evidence'].append('No supported direct object-bound semantic affirmation')
    return result
