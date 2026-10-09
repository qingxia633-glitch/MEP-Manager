"""Additive, explicit audit-to-contract mapping. Does not modify audit/source files."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).parent
def read(path): return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def source(path): return {'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}
def write(name,obj): (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

audit_path='outputs/project-rule-applicability-audit-v01/evidence.json'
gold_path='project-evidence-gate/project-evidence/garage-golden.json'
audit=read(audit_path); gold=read(gold_path)
context={'project_id':gold['project_id'],'drawing_ref':'EX-BX地下车库火灾报警平面图_t8_t3.dwg'}
rules=[]
for i,raw in enumerate(audit['rules']):
    rid=raw['rule_id']; predicates=raw['applicability_predicate']
    pairs=list(predicates.items()) if isinstance(predicates,dict) else [(p,True) for p in predicates]
    conditions=[dict(condition_id=f'{rid}:predicate:{j}',channel='object_facts',key=f'{rid}:predicate:{j}',expected=value,
                     description=text) for j,(text,value) in enumerate(pairs)]
    scope=raw['binding_scope']
    channel={'system':'system_memberships','fire_compartment':'region_memberships',
             'local_group':'local_group_memberships','drawing':'region_memberships'}[scope]
    rule=dict(rule_id=rid,rule_version='0.1',context=context,binding_scope=scope,
              conditions=conditions,scope_conditions=[dict(condition_id=f'{rid}:scope',channel=channel,
                  key=f'{rid}:scope',expected=True,description='Independently verified target membership in the rule scope')],
              exclusions=[dict(condition_id=f'{rid}:exclusion:{j}',channel='exclusions',key=f'{rid}:exclusion:{j}',
                  expected=True,description=text) for j,text in enumerate(raw['exclusions'])],
              semantic_effect={'description':raw['semantic_effect']}, specification_effect=raw['specification_effect'],
              installation_effect=None,binding_strength=raw['evidence_strength'],
              provenance=[{**source(audit_path),'pointer':f'/rules/{i}','evidence_type':'DerivedInference'}],
              source_rule=raw, mapping_note='Compound prose predicates require independent attested witnesses; absence is unknown. No natural-language inference.')
    # Named identity selectors are intentionally different from specification keys.
    if rid in ('S-line-type','SD-line-type'):
        rule['conditions'][1].update(channel='explicit_bindings',key='semantic.line_code',expected='S' if rid=='S-line-type' else 'S+D')
    if rid=='S-line-type': rule['semantic_effect']['semantic_role']='fire_alarm_bus_segment'
    if rid.startswith('plan-'):
        rule['propagation_key']=rid
    # Overlap is not itself conflict: each potential override needs its own check.
    for j,other in enumerate(raw['conflicting_rules']):
        rule['exclusions'].append(dict(condition_id=f'{rid}:override:{j}',channel='exclusions',key=f'{rid}:override:{j}',
                                     expected=True,description=f'Confirmed overriding applicability of {other}'))
    rules.append(rule)

# Separate object-bound template, not a relaxation of any of the 18 audited rules.
gold_context={k:gold[k] for k in ('project_id','drawing_ref')}
rules.append(dict(rule_id='reviewed-golden-semantic-binding',rule_version='0.1',context=gold_context,
                  binding_scope='object',target_ids=['13CF5'],conditions=[dict(condition_id='reviewed_binding',
                  channel='explicit_bindings',key='reviewed_semantic_authorization',expected='fire_alarm_bus_segment')],
                  semantic_effect={'semantic_role':'fire_alarm_bus_segment'},specification_effect=None,installation_effect=None,
                  binding_strength='project_rule_binding',exclusions=[],provenance=[source(gold_path)],
                  historical_context_note='Historical drawing_ref retained as an opaque binding identity, not rewritten.'))
write('project-rules-v01.json',dict(schema_version='0.1',sources=[source(audit_path),source(gold_path)],rules=rules))

for edge,folder in [('13C9D','electrical-shadow-run-v01'),('13CC7','electrical-shadow-run-v02')]:
    path=f'outputs/{folder}/automatic-result.json'
    automatic=read(path)
    roles=automatic['stages']['device_role']['output']
    facts=[dict(**context,target_id=r['device_handle'],target_kind='device',key='canonical_role',value=r['canonical_role'],
                status=r['role_status'],evidence_strength='drawing_fact',provenance=[{**source(path),
                'pointer':f'/stages/device_role/output/{i}'}]) for i,r in enumerate(roles)]
    write(f'{edge}.json',dict(context=context,target_object={'id':edge,'kind':'edge'},object_facts=facts,
        region_memberships=[],system_memberships=[],local_group_memberships=[],explicit_bindings=[],
        propagation_sources=[],exclusions=[],conflicting_evidence=[],provenance=[source(path),source(audit_path)],
        context_only={'geometry':'supported','endpoints':'smoke detectors','compartment_system_context':'exists',
                      'S_or_SD_edge_selection':'unresolved','note':'Context is deliberately not an edge membership witness'}))
binding=gold['bindings'][0]; evidence=gold['evidence'][0]
write('13CF5.json',dict(context=gold_context,target_object={'id':'13CF5','kind':'edge'},provenance=[source(gold_path)],
    explicit_bindings=[dict(**gold_context,target_id='13CF5',target_kind='edge',key='reviewed_semantic_authorization',
        value=evidence['semantic_role'],status=evidence['status'],evidence_strength=evidence['evidence_strength'],
        provenance=[source(gold_path),{'binding':binding,'evidence':evidence}])]))
