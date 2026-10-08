"""Eligibility and an unevaluated build plan only; no final quantity calculation."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, Context, localcontext, Inexact, Rounded, DecimalException
from quantity_contract import approved_role, physical_adjustment_identity, scope_identity, validate_measurement_evidence
from unit_contract import conversion_contract

def number(value):
    try:
        if isinstance(value,bool):return None
        d=Decimal(str(value))
        return d if d.is_finite() else None
    except (InvalidOperation,ValueError):return None

def resolve_eligibility(item):
    gate=item.get('semantic_gate',{})
    out={'model_type':'QuantityEligibilityDecision','resolver_version':'0.1','object_id':item.get('object_id'),
         'quantity_type_candidate':item.get('quantity_type_candidate'),'semantic_gate':deepcopy(gate),
         'quantity_eligibility_status':'unresolved','quantity_formula_ready':False,'quantity_formula_plan':None,
         'design_net_quantity_generation_allowed':False,'quantity_generated':False,
         'blocking_reasons':[],'limiting_evidence':[],'conflicting_evidence':[],
         'provenance':deepcopy(item.get('verified_sources',{}))}
    for key in ('measurement_scope','geometry','height','specification','multiplier','adjustments','deduplication','assumptions'):
        out[key]=deepcopy(item.get(key))
    errors=[]
    def fail(reason,status='unresolved'):
        errors.append(status);out['blocking_reasons'].append(reason)
        if status=='conflicting':out['conflicting_evidence'].append(reason)
        if status=='partial':out['limiting_evidence'].append(reason)
    if (gate.get('project_specific_status')!='supported' or gate.get('semantic_gate_passed') is not True or
        gate.get('design_net_quantity_eligible') is not True or not approved_role(gate.get('approved_semantic_role')) or
        item.get('measurement_prohibited') is True):
        out['quantity_eligibility_status']='blocked';out['blocking_reasons']=['semantic_gate_not_passed_or_measurement_prohibited'];return out
    scope=item.get('measurement_scope',{});binding=scope.get('binding',{})
    if (scope.get('status')!='supported' or scope.get('kind') not in ('edge','segment') or
        not binding.get('edge_handle') or not binding.get('drawing_ref') or not binding.get('project_id') or
        not scope.get('provenance') or (scope.get('kind')=='segment' and not binding.get('segment_id'))):
        fail('measurement_scope_missing_or_unbounded');return out
    try:
        identity = scope_identity(binding)
        if scope_identity(gate.get('object_identity')) != identity:
            raise ValueError('Gate instance identity mismatch')
        if scope_identity(gate.get('provenance',{}).get('context')) != identity:
            raise ValueError('Gate provenance identity mismatch')
        if not gate.get('accepted_evidence'):
            raise ValueError('Gate accepted identity evidence missing')
        for evidence in gate['accepted_evidence']:
            if scope_identity(evidence.get('object_identity')) != identity:
                raise ValueError('Gate accepted evidence identity mismatch')
    except ValueError as exc:
        fail('semantic_gate_full_identity_invalid:' + str(exc))
    if gate.get('edge_handle')!=binding.get('edge_handle') or gate.get('segment_id')!=binding.get('segment_id'):
        fail('scope_not_bound_to_semantic_gate')
    gate_context=gate.get('provenance',{}).get('context',{})
    if any(gate_context.get(k)!=binding.get(k) for k in ('project_id','drawing_ref')):
        fail('semantic_gate_project_or_drawing_mismatch')
    if not item.get('object_id') or not item.get('quantity_type_candidate'):fail('object_identity_missing')
    def valid(record,label,status_key='status'):
        if record.get(status_key)!='supported':fail(label+':status_not_supported')
        if not record.get('provenance'):fail(label+':provenance_missing')
        if record.get('binding')!=binding:fail(label+':scope_binding_mismatch')
    geometry=item.get('geometry',{});valid(geometry,'geometry')
    base=number(geometry.get('base_length'))
    if base is None or base<=0 or geometry.get('source_entity')!=binding.get('edge_handle'):fail('invalid_base_geometry')
    conv=geometry.get('conversion',{});valid(conv,'conversion')
    try:out['unit_conversion_contract']=deepcopy(conversion_contract(conv,binding))
    except (ValueError,TypeError,DecimalException):fail('unit_conversion_contract_invalid','conflicting')
    factor=number(conv.get('factor'));converted=number(conv.get('converted_length'))
    if not geometry.get('source_unit') or not geometry.get('engineering_unit') or factor is None or factor<=0 or converted is None:
        fail('unit_conversion_missing')
    elif base is not None:
        # Multiplication requires at most the sum of the operand coefficient lengths.
        # Independent context: caller precision, traps and rounding cannot affect admission.
        precision=max(28,len(base.as_tuple().digits)+len(factor.as_tuple().digits))
        try:
            with localcontext(Context(prec=precision)) as arithmetic:
                arithmetic.traps[Inexact]=True;arithmetic.traps[Rounded]=True
                if base*factor!=converted:fail('unit_conversion_inconsistent','conflicting')
        except DecimalException:
            fail('unit_conversion_arithmetic_not_exact','unresolved')
    if conv.get('from_unit')!=geometry.get('source_unit') or conv.get('to_unit')!=geometry.get('engineering_unit'):
        fail('conversion_unit_binding_mismatch')
    unit=geometry.get('engineering_unit')
    spec=item.get('specification',{});valid(spec,'specification','binding_status')
    if not spec.get('value') or not spec.get('installation') or spec.get('evidence_type') not in ('direct_project_binding','reviewed_project_rule'):
        fail('specification_or_installation_not_directly_bound')
    multiplier=item.get('multiplier',{});valid(multiplier,'multiplier')
    m=number(multiplier.get('value'))
    if m is None or m<=0 or not multiplier.get('interpretation'):fail('multiplier_interpretation_missing')
    height=item.get('height',{})
    if height.get('status')=='not_applicable':
        if not height.get('reason') or not height.get('provenance') or height.get('binding')!=binding:fail('height_not_applicable_without_basis')
    else:valid(height,'height')
    assumptions=item.get('assumptions',[]);aids=[a.get('id') for a in assumptions]
    if None in aids or len(set(aids))!=len(aids):fail('assumption_identity_conflict','conflicting')
    for a in assumptions:
        if a.get('status')!='approved' or not a.get('provenance') or 'value' not in a:fail('assumption_not_approved_or_sourced')
        asc=a.get('scope',{})
        if not asc:fail('assumption_scope_missing','partial');continue
        if asc.get('binding')!=binding:fail('assumption_scope_not_bound')
        conditions=asc.get('conditions',{})
        if not conditions or any(height.get('conditions',{}).get(k)!=v for k,v in conditions.items()):fail('assumption_conditions_not_satisfied')
    def assumption_refs(record,label):
        if record.get('assumptions_required') is True and not record.get('assumption_refs'):
            fail(label+':required_assumption_refs_missing')
        for ref in record.get('assumption_refs',[]):
            if ref not in aids:fail(label+':unknown_assumption_ref')
    assumption_refs(height,'height')
    path=item.get('base_path',{});valid(path,'base_path')
    plen=number(path.get('value'))
    if plen is None or plen<=0 or path.get('unit')!=unit:fail('base_path_length_or_unit_missing')
    if path.get('mode') not in ('converted_2d','approved_3d'):fail('base_path_mode_unknown')
    if path.get('mode')=='approved_3d' and height.get('status')!='supported':fail('3d_path_height_not_supported')
    if path.get('mode')=='converted_2d' and plen!=converted:fail('converted_base_path_mismatch','conflicting')
    assumption_refs(path,'base_path')
    adjustments=item.get('adjustments',{});owned=[];keys=[];ids=[];physical_keys=set()
    dedup=item.get('deduplication',{});valid(dedup,'deduplication')
    if dedup.get('key_fields')!=['edge_handle','segment_id','device','transition_type']:fail('deduplication_rule_not_explicit')
    for kind in ('transition','vertical','other'):
        group=adjustments.get(kind,{})
        if group.get('status')=='not_applicable':
            if group.get('items') or not group.get('reason') or not group.get('provenance') or group.get('binding')!=binding:
                fail(kind+':invalid_not_applicable')
            continue
        valid(group,kind)
        if group.get('inventory_complete') is not True or not isinstance(group.get('items'),list):fail(kind+':adjustment_inventory_incomplete')
        for entry in group.get('items',[]):
            valid(entry,kind+':item')
            value=number(entry.get('length'))
            if value is None or value<0 or entry.get('unit')!=unit:fail(kind+':invalid_length_or_unit')
            if entry.get('owner')!=binding:fail(kind+':foreign_adjustment_owner','conflicting')
            if entry.get('purpose')!='design_net':fail(kind+':non_design_adjustment_forbidden')
            if not entry.get('adjustment_id') or entry['adjustment_id'] in ids:fail('duplicate_or_missing_adjustment_id','conflicting')
            ids.append(entry.get('adjustment_id'));assumption_refs(entry,kind)
            try:
                physical_key=physical_adjustment_identity(entry)
                if physical_key in physical_keys:fail('duplicate_physical_adjustment','conflicting')
                physical_keys.add(physical_key)
            except ValueError:
                fail(kind+':physical_adjustment_identity_missing')
            if kind=='transition':
                key=(entry.get('owner',{}).get('edge_handle'),entry.get('owner',{}).get('segment_id'),entry.get('device'),entry.get('transition_type'))
                if not key[2] or not key[3]:fail('transition_device_or_type_missing')
                if key in keys:fail('duplicate_transition','conflicting')
                keys.append(key)
            owned.append(deepcopy(entry))
        if kind=='transition':
            expected=group.get('expected_connections')
            actual={(k[2],k[3]) for k in keys}
            if not isinstance(expected,list) or actual!={(e.get('device'),e.get('transition_type')) for e in expected}:
                fail('transition_expected_inventory_mismatch')
    claims={'multiplier':(m,'factor')}
    for e in adjustments.get('transition',{}).get('items',[]):
        key='transition:'+str(e.get('owner',{}).get('edge_handle'))+':'+str(e.get('device'))+':'+str(e.get('transition_type'))
        claims[key]=(number(e.get('length')),e.get('unit'))
    for c in item.get('measurement_claims',[]):
        if c.get('status')!='supported' or not c.get('provenance'):
            fail('measurement_claim_unresolved');continue
        key=c.get('key');value=(number(c.get('value')),c.get('unit'))
        if not key or value[0] is None:fail('measurement_claim_invalid');continue
        if key in claims and claims[key]!=value:fail('contradictory_measurement_claim:'+key,'conflicting')
        claims[key]=value
    try:
        validate_measurement_evidence({'binding':binding,'base_path':path,'owned_adjustments':owned,
                                      'geometry_basis':geometry,'height_evidence':height})
    except ValueError as exc:
        fail('measurement_evidence_contract_invalid:' + str(exc))
    if errors:
        out['quantity_eligibility_status']='conflicting' if 'conflicting' in errors else 'unresolved' if 'unresolved' in errors else 'partial'
        return out
    out['quantity_eligibility_status']='eligible';out['quantity_formula_ready']=True;out['design_net_quantity_generation_allowed']=True
    out['deduplication']['status']='supported'
    out['quantity_formula_plan']={'model_type':'QuantityBuildPlan','object_id':item['object_id'],
        'quantity_type':item['quantity_type_candidate'],'binding':deepcopy(binding),'base_path':deepcopy(path),
        'geometry_basis':deepcopy(geometry),'height_evidence':deepcopy(height),'deduplication':deepcopy(dedup),
        'owned_adjustments':owned,'multiplier':deepcopy(multiplier),'specification':deepcopy(spec),
        'formula_components':{'operator':'multiply','arguments':[{'operator':'add','references':['base_path.value']+['owned_adjustments/'+str(i)+'/length' for i in range(len(owned))]},'multiplier.value']},
        'assumptions':deepcopy(assumptions),'provenance':deepcopy(item.get('verified_sources',{})),
        'generation_allowed':True,'quantity_eligibility_status':'eligible','evaluated':False}
    return out
