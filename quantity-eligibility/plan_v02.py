"""Additive v0.2 execution-contract export. No quantity evaluation or Builder."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json

def content_hash(value):
    payload={k:v for k,v in value.items() if k!='content_hash'}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()

def seal(value):
    value['content_hash']=content_hash(value)
    return value

def export_plan(decision, source_hash, correction, policy):
    for obj in ([policy] if correction is None else [correction,policy]):
        if not isinstance(obj,dict) or obj.get('content_hash')!=content_hash(obj):raise ValueError('Evidence content hash mismatch')
    if (decision.get('quantity_eligibility_status')!='eligible' or decision.get('quantity_formula_ready') is not True or
        decision.get('design_net_quantity_generation_allowed') is not True):raise ValueError('Eligibility contract not passed')
    old=decision['quantity_formula_plan']
    if (old.get('quantity_eligibility_status')!='eligible' or old.get('generation_allowed') is not True or
        old.get('deduplication',{}).get('status')!='supported'):raise ValueError('Plan/dedup evidence not supported')
    binding=old.get('binding',{})
    def valid_ref(value):
        return isinstance(value,str) and bool(value.strip()) and '?' not in value and '\ufffd' not in value
    if correction is not None:
        if (correction.get('status')!='approved' or not correction.get('provenance') or
            correction.get('source_artifact_sha256')!=source_hash or
            not isinstance(correction.get('target_object_ids'),list) or decision['object_id'] not in correction['target_object_ids']):
            raise ValueError('Correction source/scope mismatch')
        if (binding.get('drawing_ref')!=correction.get('historical_value') or binding.get('edge_handle')!=correction.get('edge_handle') or
            not valid_ref(correction.get('corrected_value'))):
            raise ValueError('Correction target mismatch')
    elif not valid_ref(binding.get('drawing_ref')):
        raise ValueError('Invalid drawing reference requires correction evidence')
    if (policy.get('status')!='approved' or policy.get('scope',{}).get('project_id')!=binding.get('project_id') or
        policy.get('intermediate_rounding')!='none' or policy.get('rounding_mode')!='ROUND_HALF_EVEN' or
        not isinstance(policy.get('decimal_places'),int) or isinstance(policy['decimal_places'],bool) or policy['decimal_places']<0):
        raise ValueError('Reporting policy unsupported/unapproved')
    gate=decision.get('semantic_gate',{})
    if gate.get('project_specific_status')!='supported' or not gate.get('approved_semantic_role'):
        raise ValueError('Approved semantic role missing')
    p=deepcopy(old);changed=[]
    def correct(value,path=''):
        if correction is None:return
        if isinstance(value,dict):
            for key,item in value.items():
                at=path+'/'+key
                if key=='drawing_ref' and item==correction['historical_value']:
                    value[key]=correction['corrected_value'];changed.append(at)
                else:correct(item,at)
        elif isinstance(value,list):
            for i,item in enumerate(value):correct(item,path+'/'+str(i))
    correct(p)
    p.update(schema_version='0.2',quantity_formula_ready=True,generation_allowed=True,
             design_net_quantity_generation_allowed=True,approved_semantic_role=gate['approved_semantic_role'],
             reporting_policy=deepcopy(policy),source_build_plan_hash=content_hash(old),source_decision_artifact_hash=source_hash,
             source_evidence_hashes=deepcopy(old.get('provenance',{})),
             corrections_applied={'evidence':deepcopy(correction),'changed_paths':changed})
    p['deduplication']['evidence_status']=old['deduplication']['status']
    p['deduplication']['execution_status']='passed'
    p['deduplication']['execution_basis']='Upstream eligible decision and supported deduplication evidence; no recomputation'
    p['deduplication_status']='passed'
    target=old.get('base_path',{}).get('unit')
    if not target:raise ValueError('Base path unit missing')
    components=[]
    records=[('base_path.value',old['base_path'],'value')]+[
        ('owned_adjustments/'+str(i)+'/length',a,'length') for i,a in enumerate(old.get('owned_adjustments',[]))]
    precision_budget=0
    for reference,record,key in records:
        value=record.get(key);unit=record.get('unit')
        if unit!=target or not record.get('provenance'):raise ValueError('Unit/provenance incomplete; explicit conversion required')
        try:d=Decimal(str(value))
        except (InvalidOperation,ValueError):raise ValueError('Invalid numeric component')
        if not d.is_finite() or d<0 or isinstance(value,bool):raise ValueError('Nonfinite/negative numeric component')
        precision_budget+=len(d.as_tuple().digits)+abs(d.as_tuple().exponent)
        components.append({'reference':reference,'original_value':str(value),'original_unit':unit,
            'normalized_value':str(value),'normalized_unit':target,'dimension':'length',
            'conversion':{'source_unit':unit,'target_unit':target,'factor':'1','status':'approved',
                          'basis':'identity: upstream component already in target engineering unit'},
            'provenance':deepcopy(record['provenance'])})
    multiplier=old.get('multiplier',{})
    try:m=Decimal(str(multiplier['value']))
    except (KeyError,InvalidOperation,ValueError):raise ValueError('Multiplier missing')
    if not m.is_finite() or m<=0 or not multiplier.get('provenance'):raise ValueError('Multiplier invalid')
    precision_budget+=len(m.as_tuple().digits)+abs(m.as_tuple().exponent)
    p['unit_execution_contract']={'status':'approved','dimension':'length','target_unit':target,'components':components,
        'multiplier':{'original_value':str(multiplier['value']),'original_unit':'dimensionless',
            'normalized_value':str(multiplier['value']),'normalized_unit':'dimensionless','provenance':deepcopy(multiplier['provenance'])},
        'raw_geometry_conversion':deepcopy(old.get('geometry_basis',{}).get('conversion')),
        'raw_geometry_conversion_usage':'audit_only; not an additional formula term'}
    p['arithmetic_policy']={'numeric_type':'Decimal','precision':max(80,precision_budget+len(str(len(components)))+4),
        'intermediate_rounding':'none','inexact_intermediate_action':'reject','rounded_intermediate_action':'reject',
        'final_reporting_policy_ref':policy['policy_id']}
    # Also correct copied audit bindings added with the execution contract.
    correct(p)
    return seal(p)
