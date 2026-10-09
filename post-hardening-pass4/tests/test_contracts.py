import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from synthetic_contract import plan, assumption, previous, cite_synthetic, planar


class Contracts(unittest.TestCase):
    def run_plan(self,p):
        return previous.load('design-net-quantity','builder.py').build(previous.seal(p),[])
    def reject(self,p):
        r=self.run_plan(p)
        self.assertIn(r['status'],('contract_violation','invalid_plan','blocked'),r)
        self.assertNotIn('quantity',r)
    def test_valid(self):self.assertEqual(self.run_plan(plan())['status'],'built')
    def test_generic(self):
        p=plan();p['semantic_gate']['accepted_evidence'][0].update(evidence_type='manufacturer_generic',evidence_strength='external_generic');self.reject(p)
    def test_missing_binding(self):
        p=plan();p['semantic_gate'].pop('binding_targets');self.reject(p)
    def test_rejected_binding(self):
        p=plan();p['semantic_gate']['binding_targets'][0]['review_status']='rejected';self.reject(p)
    def test_reference_forward(self):
        p=plan();p['semantic_gate']['accepted_evidence'][0]['binding_id']='absent';self.reject(p)
    def test_reference_reverse(self):
        p=plan();p['semantic_gate']['binding_targets'][0]['evidence_ids']=['absent'];self.reject(p)
    def test_empty_provenance(self):
        p=plan();p['height_evidence']['provenance']=[{}];self.reject(p)
    def test_foreign_provenance(self):
        p=plan();p['height_evidence']['provenance'][0]['object_identity']['parent_path']=['OTHER'];self.reject(p)
    def test_unresolved_provenance(self):
        p=plan();p['height_evidence']['provenance'][0]['status']='unresolved';self.reject(p)
    def test_hash_not_indexed(self):
        p=plan();p['height_evidence']['provenance'][0]['sha256']='0'*64;self.reject(p)
    def test_assumption_missing_dependency(self):self.reject(assumption(plan(),['MISSING']))
    def test_assumption_existing_dependency_unsupported(self):
        p=assumption(plan(),['B']);b=copy.deepcopy(p['assumptions'][0]);b.update(id='B');b.pop('assumptions_required');b.pop('assumption_refs');p['assumptions'].append(b);self.reject(p)
    def test_assumption_false_declaration_unsupported(self):
        p=assumption(plan());p['assumptions'][0]['assumptions_required']=False;self.reject(p)
    def test_leaf_assumption_positive(self):self.assertEqual(self.run_plan(assumption(plan()))['status'],'built')
    def test_duplicate_evidence(self):
        p=plan();p['semantic_gate']['accepted_evidence']*=2;self.reject(p)
    def test_duplicate_binding(self):
        p=plan();p['semantic_gate']['binding_targets']*=2;self.reject(p)
    def test_binding_foreign(self):
        p=plan();p['semantic_gate']['binding_targets'][0]['parent_path']=['OTHER'];self.reject(p)
    def test_binding_role(self):
        p=plan();p['semantic_gate']['binding_targets'][0]['semantic_role']='other';self.reject(p)
    def test_binding_assertion(self):
        p=plan();p['semantic_gate']['binding_targets'][0]['assertion']='deny';self.reject(p)
    def test_profile_missing(self):
        p=plan();del p['admission_contracts'];self.reject(p)
    def test_required_provenance_roots(self):
        for key in ('base_path','multiplier','specification','deduplication','geometry_basis','height_evidence'):
            with self.subTest(key=key):
                p=plan();p[key].pop('provenance');self.reject(p)
    def test_adjustment_provenance(self):
        p=plan();p['owned_adjustments'][0]['provenance']=[{}];self.reject(p)
    def test_source_index_foreign(self):
        p=plan();sid=p['height_evidence']['provenance'][0]['source_id'];p['source_evidence_hashes'][sid]['object_identity']['parent_path']=['OTHER'];p['provenance']=copy.deepcopy(p['source_evidence_hashes']);self.reject(p)
    def test_source_index_unresolved(self):
        p=plan();sid=p['height_evidence']['provenance'][0]['source_id'];p['source_evidence_hashes'][sid]['status']='unresolved';p['provenance']=copy.deepcopy(p['source_evidence_hashes']);self.reject(p)
    def test_wrong_evidence_reference(self):
        p=plan();p['height_evidence']['provenance'][0]['evidence_ref']='/specification';self.reject(p)
    def test_wrong_binding_reference(self):
        p=plan();p['height_evidence']['provenance'][0]['binding_ref']='/other';self.reject(p)
    def test_extra_unbound_hash(self):
        p=plan();p['source_evidence_hashes']['unbound']=dict(next(iter(p['source_evidence_hashes'].values())),source_id='unbound',evidence_refs=['/missing']);p['provenance']=copy.deepcopy(p['source_evidence_hashes']);self.reject(p)
    def test_native_replay_positive(self):
        p=plan();m=previous.load('design-net-quantity','builder.py');q=m.build(p,[])['quantity'];self.assertEqual(m.replay_validate(p,q)['status'],'replay_matched')
    def test_replay_source_change(self):
        p=plan();m=previous.load('design-net-quantity','builder.py');q=m.build(p,[])['quantity'];sid=p['height_evidence']['provenance'][0]['source_id'];p['height_evidence']['provenance'][0]['sha256']='f'*64;p['source_evidence_hashes'][sid]['sha256']='f'*64;p['provenance']=copy.deepcopy(p['source_evidence_hashes']);r=m.replay_validate(previous.seal(p),q);self.assertTrue(r['numeric_match']);self.assertEqual(r['status'],'replay_mismatch')
    def test_unresolved_gate(self):
        p=plan();p['semantic_gate']['project_specific_status']='unresolved';self.reject(p)
    def test_wrong_physical_units(self):
        p=plan();p['geometry_basis']['source_unit']='mm';p['geometry_basis']['conversion'].update(from_unit='mm',factor='1');p['unit_conversion_contract'].update(source_unit='mm',factor='1');p['unit_execution_contract']['raw_geometry_conversion']=copy.deepcopy(p['geometry_basis']['conversion']);self.reject(p)
    def test_legacy_blocked(self):
        p=plan();p['schema_version']='0.2';self.assertEqual(self.run_plan(p)['status'],'blocked')
    def export_input(self):
        p=plan()
        for sid in list(p['source_evidence_hashes']):
            if '/unit_execution_contract/' in sid:p['source_evidence_hashes'].pop(sid)
        p['provenance']=copy.deepcopy(p['source_evidence_hashes'])
        d=dict(object_id=p['object_id'],quantity_eligibility_status='eligible',quantity_formula_ready=True,
            design_net_quantity_generation_allowed=True,semantic_gate=copy.deepcopy(p['semantic_gate']),
            quantity_formula_plan=p,unit_conversion_contract=copy.deepcopy(p['unit_conversion_contract']))
        return p,d
    def test_export_and_build(self):
        p,d=self.export_input();e=previous.load('quantity-eligibility','plan_v03.py')
        out=e.export_plan(d,'a'*64,None,p['reporting_policy']);self.assertEqual(self.run_plan(out)['status'],'built')
    def test_export_rejects_weak(self):
        p,d=self.export_input();p['semantic_gate']['accepted_evidence'][0]['evidence_type']='manufacturer_generic';d['semantic_gate']=copy.deepcopy(p['semantic_gate'])
        with self.assertRaises(ValueError):previous.load('quantity-eligibility','plan_v03.py').export_plan(d,'a'*64,None,p['reporting_policy'])
    def test_current_planar_exemption(self):self.assertEqual(self.run_plan(planar())['status'],'built')
    def test_exemption_source_missing(self):
        p=planar();p['height_evidence']['measurement_rule']['provenance']=[{}];self.reject(p)
    def test_invalid_optional_rule_shape(self):
        p=plan();p['height_evidence']['measurement_rule']='invalid';self.reject(p)
    def test_current_cad_scale(self):
        p=plan();g=p['geometry_basis'];g.update(base_length='10000',source_unit='drawing_unit')
        c=dict(contract_id='synthetic-scale',version='1',kind='cad_geometry_scale',status='approved',binding=copy.deepcopy(p['binding']),source_unit='drawing_unit',target_unit='m',factor='0.001')
        cite_synthetic(p,c,'/geometry_basis/conversion/reviewed_scale_contract');previous.seal(c)
        g['conversion'].update(from_unit='drawing_unit',factor='0.001',conversion_kind='cad_geometry_scale',reviewed_scale_contract=copy.deepcopy(c))
        p['unit_conversion_contract']=copy.deepcopy(c);p['unit_execution_contract']['raw_geometry_conversion']=copy.deepcopy(g['conversion'])
        self.assertEqual(self.run_plan(p)['status'],'built')
        g['conversion']['reviewed_scale_contract']['provenance']=[{}];previous.seal(g['conversion']['reviewed_scale_contract']);p['unit_conversion_contract']=copy.deepcopy(g['conversion']['reviewed_scale_contract']);p['unit_execution_contract']['raw_geometry_conversion']=copy.deepcopy(g['conversion']);self.reject(p)
    def test_replay_approved_assumption_value_change(self):
        p=assumption(plan());m=previous.load('design-net-quantity','builder.py');q=m.build(previous.seal(p),[])['quantity']
        p['assumptions'][0]['value']='another explicit synthetic assumption'
        r=m.replay_validate(previous.seal(p),q);self.assertTrue(r['numeric_match']);self.assertEqual(r['status'],'replay_mismatch')
    def test_replay_exemption_review_change(self):
        p=planar();m=previous.load('design-net-quantity','builder.py');q=m.build(p,[])['quantity']
        p['height_evidence']['measurement_rule']['rule_id']='new-reviewed-rule'
        r=m.replay_validate(previous.seal(p),q);self.assertTrue(r['numeric_match']);self.assertEqual(r['status'],'replay_mismatch')
    def test_replay_owner_change_rejected(self):
        p=plan();m=previous.load('design-net-quantity','builder.py');q=m.build(p,[])['quantity'];p['owned_adjustments'][0]['owner']['parent_path']=['OTHER'];r=m.replay_validate(previous.seal(p),q);self.assertEqual(r['status'],'contract_violation')


if __name__=='__main__':unittest.main()
