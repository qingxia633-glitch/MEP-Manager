import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

MODULE=Path(__file__).resolve().parents[1]
ROOT=MODULE.parent
sys.path.insert(0,str(MODULE))
from resolver import resolve,to_gate_evidence
from rules import load_rules

CTX={'project_id':'test','drawing_ref':'drawing'}
def rule(channel='object_facts',key='required',expected=True):
    return dict(rule_id='test-rule',rule_version='0.1',context=CTX,binding_scope='object',
                conditions=[dict(condition_id='required',channel=channel,key=key,expected=expected)],
                semantic_effect={'semantic_role':'test_semantic_role'},provenance=['synthetic'])
def request(): return dict(context=CTX,target_object={'id':'edge','kind':'edge'},provenance=['synthetic'])
def witness(key='required',value=True,**kw):
    return dict(dict(**CTX,target_id='edge',target_kind='edge',key=key,value=value,status='supported',
                     evidence_strength='direct_object_binding',provenance=['synthetic']),**{}) | kw

class ResolverTests(unittest.TestCase):
    def status(self,r,q): return resolve(r,q)['applicability_status']
    def test_all_required_true(self):
        q=request();q['object_facts']=[witness()]
        self.assertEqual(self.status(rule(),q),'applicable')
    def test_false_required(self):
        q=request();q['object_facts']=[witness(value=False)]
        self.assertEqual(self.status(rule(),q),'not_applicable')
    def test_unknown_required(self): self.assertEqual(self.status(rule(),request()),'unresolved')
    def test_same_rank_conflict(self):
        q=request();q['object_facts']=[witness(),witness(value=False)]
        self.assertEqual(self.status(rule(),q),'conflicting')
    def test_specification_cannot_reverse_identity(self):
        q=request();q['object_facts']=[witness(key='specification',value='WDZN-RYJS-2x1.5')]
        self.assertEqual(self.status(rule('explicit_bindings','semantic.line_code','S'),q),'unresolved')
    def test_unknown_s_sd_selection(self):
        q=request();q['explicit_bindings']=[witness(key='semantic.line_code',value='S',status='partial')]
        self.assertEqual(self.status(rule('explicit_bindings','semantic.line_code','S'),q),'unresolved')
    def propagation(self):
        r=rule();r['propagation_key']='rest';q=request();q['object_facts']=[witness()]
        def proven(value):return dict(value=value,status='supported',provenance=['synthetic independent scope review'])
        q['propagation_sources']=[witness(key='rest',source_annotation='text:1',root_target={'id':'root','kind':'edge','status':'supported','provenance':['synthetic root review']},
            propagation_relation=proven('explicit local set'),bounded_set=[{'id':'edge','kind':'edge'}],
            propagation_boundary=proven('closed reviewed local set'),termination_condition=proven('outside set stops'))]
        return r,q
    def test_bounded_rest_inside(self):
        r,q=self.propagation();self.assertEqual(self.status(r,q),'applicable')
    def test_shared_propagation_source_does_not_need_edge_specific_annotation(self):
        r,q=self.propagation()
        del q['propagation_sources'][0]['target_id'];del q['propagation_sources'][0]['target_kind']
        self.assertEqual(self.status(r,q),'applicable')
    def test_foreign_propagation_source_cannot_cover_target(self):
        r,q=self.propagation();q['propagation_sources'][0]['drawing_ref']='another drawing'
        self.assertEqual(self.status(r,q),'unresolved')
    def test_bounded_rest_outside(self):
        r,q=self.propagation();q['propagation_sources'][0]['bounded_set']=[{'id':'other','kind':'edge'}]
        self.assertEqual(self.status(r,q),'not_applicable')
    def test_rest_missing_each_boundary_requirement(self):
        for key in ('source_annotation','root_target','propagation_relation','bounded_set','propagation_boundary','termination_condition'):
            with self.subTest(key=key):
                r,q=self.propagation();del q['propagation_sources'][0][key]
                self.assertEqual(self.status(r,q),'unresolved')
    def test_device_membership_not_edge(self):
        q=request();q['system_memberships']=[witness(target_kind='device')]
        self.assertEqual(self.status(rule('system_memberships'),q),'unresolved')
    def test_missing_region(self): self.assertEqual(self.status(rule('region_memberships'),request()),'unresolved')
    def test_exclusion_hit(self):
        r=rule();r['exclusions']=[dict(condition_id='excluded',channel='exclusions',key='excluded',expected=True)]
        q=request();q['object_facts']=[witness()];q['exclusions']=[witness(key='excluded')]
        self.assertEqual(self.status(r,q),'not_applicable')
    def test_exclusion_unknown_blocks(self):
        r=rule();r['exclusions']=[dict(condition_id='excluded',channel='exclusions',key='excluded',expected=True)]
        q=request();q['object_facts']=[witness()];self.assertEqual(self.status(r,q),'unresolved')
    def test_weak_evidence_and_confidence_do_not_fill_unknown(self):
        for strength in ('pattern_only','contextual_only','external_generic'):
            q=request();q['candidate_confidence']='high';q['object_facts']=[witness(evidence_strength=strength)]
            self.assertEqual(self.status(rule(),q),'unresolved')
    def test_foreign_context_or_target_ignored(self):
        for change in ({'project_id':'foreign'},{'drawing_ref':'foreign'},{'target_id':'other'},{'provenance':[]}):
            q=request();q['object_facts']=[witness(**change)]
            self.assertEqual(self.status(rule(),q),'unresolved')
    def test_rule_context_mismatch(self):
        r=rule();r['context']={'project_id':'other','drawing_ref':'drawing'}
        q=request();q['object_facts']=[witness()];self.assertEqual(self.status(r,q),'unresolved')
    def test_pending_evidence_not_hidden_by_supported(self):
        q=request();q['object_facts']=[witness(),witness(status='unresolved')]
        self.assertEqual(self.status(rule(),q),'unresolved')
    def test_false_precedence_retains_conflict(self):
        r=rule();r['conditions'].append(dict(condition_id='second',channel='object_facts',key='second',expected=True))
        q=request();q['object_facts']=[witness(value=False),witness(key='second',status='conflicting')]
        result=resolve(r,q);self.assertEqual(result['applicability_status'],'not_applicable')
        self.assertEqual(result['conflicting_conditions'],['second'])
    def test_bool_numeric_not_equivalent(self):
        q=request();q['object_facts']=[witness(value=1)]
        self.assertEqual(self.status(rule(),q),'not_applicable')
    def test_peer_values_with_different_types_conflict(self):
        q=request();q['object_facts']=[witness(value=True),witness(value=1)]
        self.assertEqual(self.status(rule(),q),'conflicting')
    def test_empty_rules_not_vacuously_true(self):
        r=rule();r['conditions']=[];self.assertEqual(self.status(r,request()),'unresolved')
    def test_null_witness_is_unknown(self):
        q=request();q['object_facts']=[witness(value=None)]
        self.assertEqual(self.status(rule(),q),'unresolved')
    def test_invalid_scope_rejected(self):
        r=rule();r['binding_scope']='unbounded-everywhere'
        with self.assertRaises(ValueError):resolve(r,request())
    def test_missing_condition_contract_rejected(self):
        for field in ('key','expected'):
            r=rule();del r['conditions'][0][field]
            with self.assertRaises(ValueError):resolve(r,request())
    def test_duplicate_condition_ids_rejected(self):
        r=rule();r['conditions']*=2
        with self.assertRaises(ValueError):resolve(r,request())
    def test_propagation_conflict(self):
        r,q=self.propagation();other=copy.deepcopy(q['propagation_sources'][0]);other['root_target']['id']='different'
        q['propagation_sources'].append(other);self.assertEqual(self.status(r,q),'conflicting')
    def test_system_rule_cannot_omit_membership_contract(self):
        r=rule();r['binding_scope']='system';q=request();q['object_facts']=[witness()]
        self.assertEqual(self.status(r,q),'unresolved')
    def test_explicit_region_scope(self):
        r=rule();r['binding_scope']='region';r['scope_conditions']=[dict(condition_id='region',channel='region_memberships',key='compartment',expected='one')]
        q=request();q['object_facts']=[witness()];q['region_memberships']=[witness(key='compartment',value='one')]
        self.assertEqual(self.status(r,q),'applicable')
    def test_device_compartment_not_s_identity(self):
        q=request();q['region_memberships']=[witness(key='compartment',value='one',target_id='a',target_kind='device'),
                                             witness(key='compartment',value='one',target_id='b',target_kind='device')]
        self.assertEqual(self.status(rule('explicit_bindings','semantic.line_code','S'),q),'unresolved')
    def test_empty_proven_bounded_set_excludes_target(self):
        r,q=self.propagation();q['propagation_sources'][0]['bounded_set']=[]
        self.assertEqual(self.status(r,q),'not_applicable')
    def test_actual_s_and_sd_conflict(self):
        q=request();q['explicit_bindings']=[witness(key='semantic.line_code',value='S'),witness(key='semantic.line_code',value='S+D')]
        self.assertEqual(self.status(rule('explicit_bindings','semantic.line_code','S'),q),'conflicting')
    def test_no_approval_or_quantity_fields(self):
        q=request();q['object_facts']=[witness()];result=resolve(rule(),q)
        self.assertNotIn('project_specific_status',result);self.assertNotIn('design_net_quantity',result)
    def test_gate_adapter_pending_only(self):
        q=request();q['object_facts']=[witness()];proposal=resolve(rule(),q)
        bundle=to_gate_evidence(proposal)
        sys.path.insert(0,str(ROOT/'project-evidence-gate'))
        try:
            spec=importlib.util.spec_from_file_location('gate_for_integration',ROOT/'project-evidence-gate/resolver.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            result=module.evaluate_semantics({'edge_handle':'edge','candidate_role':'unknown'},bundle,CTX)
            self.assertFalse(result['semantic_gate_passed'])
            # Explicit external review in a synthetic integration test, never performed by resolver.
            bundle['bindings'][0]['review_status']='reviewed';bundle['evidence'][0]['status']='supported'
            result=module.evaluate_semantics({'edge_handle':'edge','candidate_role':'unknown'},bundle,CTX)
            self.assertTrue(result['semantic_gate_passed'])
        finally:sys.path.pop(0)
    def test_unresolved_adapter_blocked(self):
        with self.assertRaises(ValueError):to_gate_evidence(resolve(rule(),request()))

class ProjectFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules=load_rules(MODULE/'fixtures/project-rules-v01.json',ROOT)
    def fixture(self,edge):return json.loads((MODULE/f'fixtures/{edge}.json').read_text(encoding='utf-8'))
    def test_all_18_source_rules_preserved(self):
        original=json.loads((ROOT/'outputs/project-rule-applicability-audit-v01/evidence.json').read_text(encoding='utf-8-sig'))
        self.assertEqual([r['source_rule'] for r in self.rules[:18]],original['rules'])
    def test_13C9D(self):
        r=resolve(self.rules[0],self.fixture('13C9D'))
        self.assertEqual(r['applicability_status'],'unresolved');self.assertFalse(r['may_submit_to_project_gate'])
    def test_13CC7(self):
        r=resolve(self.rules[0],self.fixture('13CC7'))
        self.assertEqual(r['applicability_status'],'unresolved');self.assertFalse(r['may_submit_to_project_gate'])
    def test_golden_positive(self):
        r=resolve(self.rules[-1],self.fixture('13CF5'))
        self.assertEqual(r['applicability_status'],'applicable');self.assertTrue(r['may_submit_to_project_gate'])
    def test_golden_source_assertions_and_hashes(self):
        spec=importlib.util.spec_from_file_location('gate_source_validation',ROOT/'project-evidence-gate/evidence.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        bundle=module.load_bundle(ROOT/'project-evidence-gate/project-evidence/garage-golden.json')
        self.assertEqual(bundle['bindings'][0]['edge_handle'],'13CF5')
    def test_golden_authorization_not_transferable(self):
        q=self.fixture('13CF5');q['target_object']['id']='13CC7';q['explicit_bindings'][0]['target_id']='13CC7'
        self.assertEqual(resolve(self.rules[-1],q)['applicability_status'],'not_applicable')
    def test_deterministic_and_no_input_mutation(self):
        q=self.fixture('13CF5');before=copy.deepcopy(q)
        self.assertEqual(resolve(self.rules[-1],q),resolve(self.rules[-1],q));self.assertEqual(q,before)

if __name__=='__main__':unittest.main()
