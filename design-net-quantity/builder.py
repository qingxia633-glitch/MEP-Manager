"""Execute reviewed v0.2 contracts. No CAD, semantic or ownership inference."""
from copy import deepcopy
from decimal import Decimal, localcontext, Inexact, Rounded, ROUND_HALF_EVEN, DecimalException
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.builder-deps'))
from jsonschema import Draft202012Validator
sys.path.insert(0,str(ROOT/'quantity-eligibility'))
from quantity_contract import scope_identity, validate_plan_bindings

VERSION='0.1'
SCHEMA=json.loads((ROOT/'quantity-eligibility/schemas/quantity-build-plan-v02.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR=Draft202012Validator(SCHEMA)

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()

def seal(value):
    value['content_hash']=digest({k:v for k,v in value.items() if k!='content_hash'})
    return value

def verify(value):
    if value.get('content_hash')!=digest({k:v for k,v in value.items() if k!='content_hash'}):
        raise ValueError('content_hash mismatch')

def decimal(value):
    if isinstance(value,(bool,float)) or not isinstance(value,(str,int)):
        raise ValueError('Exact decimal string/integer required')
    d=Decimal(value)
    if not d.is_finite() or d<0: raise ValueError('Nonnegative finite value required')
    return d

def result(status,reason=None,errors=None,**extra):
    return {'status':status,'blocking_reasons':[reason] if reason else [],'validation_errors':errors or [],**extra}

def key(q):
    return (scope_identity(q['scope']),q['quantity_kind'],q['approved_semantic_role'])

def semantic_content(value, root=True):
    # Locators are retained in output, but do not affect quantity content identity.
    if isinstance(value,dict):
        return {k:semantic_content(v, False) for k,v in value.items() if k not in
                {'built_at','path','source_build_plan_hash','source_decision_artifact_hash'} and
                not (root and k=='content_hash')}
    if isinstance(value,list): return [semantic_content(v, False) for v in value]
    return value


def evidence_content(value, location=()):
    """Only a hash-identified source's machine locator is non-semantic.

    Unlike the display/content hash filter, no arbitrary nested field name is
    dropped from the reviewed execution evidence contract.
    """
    if isinstance(value,dict):
        source_record = (len(location)==3 and location[0]=='records' and
                         location[1] in ('source_evidence_hashes','provenance'))
        return {k:evidence_content(v, location+(k,)) for k,v in value.items()
                if not (source_record and k=='path' and isinstance(value.get('sha256'),str) and len(value['sha256'])==64)}
    if isinstance(value,list):return [evidence_content(v, location+(i,)) for i,v in enumerate(value)]
    return value


def execution_evidence_contract(plan):
    fields=('binding','approved_semantic_role','specification','geometry_basis','height_evidence',
            'base_path','owned_adjustments','multiplier','deduplication','assumptions',
            'corrections_applied','source_evidence_hashes','provenance','formula_components',
            'unit_execution_contract','unit_conversion_contract','reporting_policy','arithmetic_policy',
            'semantic_gate','approved_semantic_binding','height_requirement')
    return {'version':'2','records':{k:deepcopy(plan.get(k)) for k in fields}}

def _execute(p):
    errors=[{'path':'/'+ '/'.join(map(str,e.absolute_path)),'message':e.message} for e in VALIDATOR.iter_errors(p)]
    if errors:
        blocked=isinstance(p,dict) and (p.get('quantity_eligibility_status') not in (None,'eligible') or
                p.get('quantity_formula_ready') is False or p.get('generation_allowed') is False)
        return result('blocked' if blocked else 'invalid_plan','Schema/eligibility admission failed',errors)
    try:
        verify(p)
        validate_plan_bindings(p)
        policy=p['reporting_policy']; verify(policy)
        if not policy.get('provenance') or policy['status']!='approved' or policy['scope']['project_id']!=p['binding']['project_id']:
            raise ValueError('Reporting policy scope/approval mismatch')
        if not p['provenance'] or not p['source_evidence_hashes']: raise ValueError('Missing provenance')
        a=p['arithmetic_policy']
        if (a['numeric_type']!='Decimal' or a['intermediate_rounding']!='none' or
            a['inexact_intermediate_action']!='reject' or a['rounded_intermediate_action']!='reject' or
            a.get('final_reporting_policy_ref')!=policy['policy_id']): raise ValueError('Unsupported arithmetic contract')
        if type(a['precision']) is not int or not 1<=a['precision']<=10000: raise ValueError('Invalid precision')
        if policy['decimal_places']>1000: raise ValueError('Reporting precision limit')
        u=p['unit_execution_contract']; terms=u['components']
        records=[p['base_path']]+p['owned_adjustments']
        refs=['base_path.value']+[f'owned_adjustments/{i}/length' for i in range(len(records)-1)]
        expected={'operator':'multiply','arguments':[{'operator':'add','references':refs},'multiplier.value']}
        if p['formula_components']!=expected: raise ValueError('Unsupported/inconsistent formula')
        if len(terms)!=len(records): raise ValueError('Unit component inventory mismatch')
        if len({r['unit'] for r in records})!=1: raise ValueError('Mixed-unit plan unsupported in v0.1')
        if u['target_unit'] not in ('m','mm'): raise ValueError('Unsupported target length unit')
        correction=p['corrections_applied'].get('evidence')
        if not correction and p['corrections_applied'].get('changed_paths'):
            raise ValueError('Correction paths without correction evidence')
        if correction:
            verify(correction)
            if (correction['status']!='approved' or p['object_id'] not in correction['target_object_ids'] or
                correction['edge_handle']!=p['binding']['edge_handle'] or
                correction['corrected_value']!=p['binding']['drawing_ref']): raise ValueError('Correction binding mismatch')
        with localcontext() as c:
            c.prec=a['precision'];c.traps[Inexact]=True;c.traps[Rounded]=True
            values=[]
            for i,(r,t,ref) in enumerate(zip(records,terms,refs)):
                v=decimal(r['value' if i==0 else 'length']); conversion=t['conversion']
                if not r.get('provenance') or not t.get('provenance'): raise ValueError('Missing component provenance')
                if (t['reference']!=ref or decimal(t['original_value'])!=v or t['original_unit']!=r['unit'] or
                    t['normalized_unit']!=u['target_unit'] or t['dimension']!='length' or
                    conversion['source_unit']!=r['unit'] or conversion['target_unit']!=u['target_unit'] or
                    conversion['status']!='approved'): raise ValueError('Unit execution contract mismatch')
                factor=decimal(conversion['factor'])
                expected_factor={('m','m'):Decimal(1),('mm','mm'):Decimal(1),('mm','m'):Decimal('0.001'),('m','mm'):Decimal(1000)}
                if factor!=expected_factor.get((r['unit'],u['target_unit'])): raise ValueError('Invalid length conversion factor')
                value=v*factor
                if value!=decimal(t['normalized_value']): raise ValueError('Normalized value mismatch')
                values.append(value)
            m=decimal(p['multiplier']['value']); um=u['multiplier']
            if m<=0: raise ValueError('Positive multiplier required')
            if (not p['multiplier'].get('provenance') or not um.get('provenance') or
                um['original_unit']!='dimensionless' or um['normalized_unit']!='dimensionless' or
                decimal(um['original_value'])!=m or decimal(um['normalized_value'])!=m): raise ValueError('Multiplier contract mismatch')
            exact=sum(values,Decimal(0))*m
            c.traps[Inexact]=False;c.traps[Rounded]=False
            reported=exact.quantize(Decimal(1).scaleb(-policy['decimal_places']),rounding=ROUND_HALF_EVEN)
        q={'object_type':'DesignNetQuantity','quantity_kind':p['quantity_type'],'scope':deepcopy(p['binding']),
           'approved_semantic_role':p['approved_semantic_role'],'specification':p['specification']['value'],
           'installation_method':p['specification']['installation'],
           'formula':{'base_path':deepcopy(p['base_path']),'owned_adjustments':deepcopy(p['owned_adjustments']),
                      'multiplier':deepcopy(p['multiplier']),'expression':deepcopy(p['formula_components'])},
           'computed_quantity':{'exact_value':str(exact),'reported_value':str(reported),'unit':u['target_unit'],
                                'decimal_places':policy['decimal_places'],'rounding_mode':policy['rounding_mode']},
           'unit_execution_contract':deepcopy(u),'reporting_policy':deepcopy(policy),
           'provenance':deepcopy(p['provenance']),'assumptions':deepcopy(p['assumptions']),
           'source_build_plan_hash':p['content_hash'],'source_evidence_hashes':deepcopy(p['source_evidence_hashes']),
           'correction_evidence_refs':[{'id':correction['correction_id'],'content_hash':correction['content_hash']}] if correction else [],
           'builder_version':VERSION}
        q['evidence_contract']=execution_evidence_contract(p)
        q['evidence_contract_digest']=digest(evidence_content(q['evidence_contract']))
        q['quantity_id']='design-net:'+digest(key(q))
        q['content_hash']=digest(semantic_content(q))
        return result('built',quantity=q)
    except (ValueError,KeyError,TypeError,DecimalException) as e:
        return result('contract_violation',str(e))

def build(plan,existing_quantities=None):
    r=_execute(plan)
    if r['status']!='built': return r
    if not isinstance(existing_quantities,list): return result('blocked','Explicit complete quantity registry required')
    try:
        if any(key(q)==key(r['quantity']) for q in existing_quantities):
            return result('duplicate_detected','Scope/kind/approved role already issued')
    except (KeyError,TypeError): return result('contract_violation','Invalid registry entry')
    return r

def replay_validate(plan,frozen_quantity):
    r=_execute(plan)
    if r['status']!='built': return r
    q=r['quantity']
    try:
        frozen_multiplier=(frozen_quantity['multiplier'] if 'multiplier' in frozen_quantity
                           else frozen_quantity['formula']['multiplier']['value'])
        matches=(key(q)==key(frozen_quantity) and q['specification']==frozen_quantity['specification'] and
                 q['installation_method']==frozen_quantity['installation_method'] and
                 q['computed_quantity']['unit']==frozen_quantity['computed_quantity']['unit'] and
                 decimal(q['computed_quantity']['reported_value'])==decimal(frozen_quantity['computed_quantity']['reported_value']) and
                 decimal(plan['multiplier']['value'])==decimal(frozen_multiplier))
    except (KeyError,TypeError,ValueError,DecimalException): matches=False
    native='builder_version' in frozen_quantity
    contract_match=False
    if native:
        required=set(q)
        if required.issubset(frozen_quantity):
            contract_match=(frozen_quantity.get('content_hash')==digest(semantic_content(frozen_quantity)) and
                            frozen_quantity.get('evidence_contract_digest')==digest(evidence_content(frozen_quantity.get('evidence_contract'))) and
                            q['evidence_contract_digest']==frozen_quantity['evidence_contract_digest'] and
                            evidence_content(q['evidence_contract'])==evidence_content(frozen_quantity['evidence_contract']) and
                            semantic_content(q)==semantic_content(frozen_quantity))
        status='replay_matched' if matches and contract_match else 'replay_mismatch'
    else:
        status='replay_value_matched_legacy_evidence_incomplete' if matches else 'replay_mismatch'
    return result(status,None if status=='replay_matched' else 'Full frozen evidence contract not matched',
                  replay_status='matched' if status=='replay_matched' else 'legacy_evidence_incomplete' if matches and not native else 'mismatch',
                  numeric_match=matches,evidence_contract_match=contract_match,quantity=q,issued=False)
