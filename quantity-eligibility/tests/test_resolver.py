import copy
import json
import sys
import unittest
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'quantity-eligibility'))
from evidence import load_evidence
from resolver import resolve_eligibility

class Eligibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixtures=load_evidence(ROOT/'quantity-eligibility/fixtures/golden.json')['objects']
    def item(self):return copy.deepcopy(self.fixtures[0])
    def check_no(self,x,status=None):
        r=resolve_eligibility(x)
        self.assertFalse(r['design_net_quantity_generation_allowed'])
        self.assertFalse(r['quantity_formula_ready'])
        self.assertIsNone(r['quantity_formula_plan'])
        if status:self.assertEqual(r['quantity_eligibility_status'],status)
        return r

    def test_golden_conduit_wire_and_no_final_value(self):
        for x in self.fixtures:
            r=resolve_eligibility(x)
            self.assertEqual(r['quantity_eligibility_status'],'eligible',r['blocking_reasons'])
            self.assertTrue(r['quantity_formula_ready'])
            self.assertEqual(r['quantity_formula_plan']['model_type'],'QuantityBuildPlan')
            self.assertFalse(r['quantity_generated'])
            self.assertNotIn('total_length',r['quantity_formula_plan'])
            self.assertEqual(len(r['quantity_formula_plan']['owned_adjustments']),2)

    def test_wire_multiplier_not_parsed_from_spec(self):
        r=resolve_eligibility(self.fixtures[1])
        self.assertEqual(r['quantity_formula_plan']['multiplier']['value'],1)
        x=copy.deepcopy(self.fixtures[1]);x['multiplier']['provenance']=[]
        self.check_no(x,'unresolved')

    def test_real_gate_negative(self):
        gates=json.loads((ROOT/'outputs/project-evidence-gate-v01/fixture-results.json').read_text(encoding='utf-8'))
        for gate in gates[1:]:
            x=self.item();x['semantic_gate']=gate
            self.check_no(x,'blocked')

    def test_all_gate_flags(self):
        for key,value in [('project_specific_status','partial'),('semantic_gate_passed',False),('design_net_quantity_eligible',False)]:
            x=self.item();x['semantic_gate'][key]=value;self.check_no(x,'blocked')

    def test_missing_spec(self):
        x=self.item();del x['specification'];self.check_no(x,'unresolved')

    def test_missing_scope(self):
        x=self.item();x['measurement_scope']={};self.check_no(x,'unresolved')

    def test_missing_geometry_provenance(self):
        x=self.item();x['geometry']['provenance']=[];self.check_no(x,'unresolved')

    def test_units_unknown_and_conversion_mismatch(self):
        x=self.item();x['geometry']['conversion']['status']='unresolved';self.check_no(x,'unresolved')
        x=self.item();x['geometry']['conversion']['converted_length']='1';self.check_no(x,'conflicting')

    def test_height_required_missing(self):
        x=self.item();del x['height'];self.check_no(x,'unresolved')

    def test_missing_assumption_scope(self):
        x=self.item();x['assumptions'][0]['scope']={};self.check_no(x,'partial')

    def test_wrong_assumption_conditions(self):
        x=self.item();x['height']['conditions']['slabThicknessMm']=350;self.check_no(x,'unresolved')

    def test_transition_other_edge(self):
        x=self.item();x['adjustments']['transition']['items'][0]['owner']['edge_handle']='13CEF';self.check_no(x,'conflicting')

    def test_transition_duplicate(self):
        x=self.item();x['adjustments']['transition']['items'].append(copy.deepcopy(x['adjustments']['transition']['items'][0]));self.check_no(x,'conflicting')

    def test_missing_transition(self):
        x=self.item();x['adjustments']['transition']['items'].pop();self.check_no(x,'unresolved')

    def test_transition_status_and_source(self):
        for key,value in [('status','unresolved'),('provenance',[])]:
            x=self.item();x['adjustments']['transition']['items'][0][key]=value;self.check_no(x,'unresolved')

    def test_absence_not_zero(self):
        for name in ['vertical','other']:
            x=self.item();del x['adjustments'][name];self.check_no(x,'unresolved')

    def test_procurement_does_not_block(self):
        x=self.item();x['procurement']={'ConduitMaterialRequirement':'partial','wall_thickness':None,'brand':None};x['pricing']={'status':'unresolved'}
        self.assertEqual(resolve_eligibility(x)['quantity_eligibility_status'],'eligible')

    def test_measurement_conflict(self):
        x=self.item();x['measurement_claims']=[{'key':'transition:13CF5:12D55:box_entry','value':'0.150','unit':'m','status':'supported','provenance':[{'source_id':'rules'}]},
          {'key':'transition:13CF5:12D55:box_entry','value':'0.200','unit':'m','status':'supported','provenance':[{'source_id':'rules'}]}]
        self.check_no(x,'conflicting')

    def test_context_only_spec_blocked(self):
        x=self.item();x['specification']['evidence_type']='nearby_text';self.check_no(x,'unresolved')

    def test_no_mutation(self):
        x=self.item();before=copy.deepcopy(x);resolve_eligibility(x);self.assertEqual(x,before)

    def test_multiplier_cannot_override_bound_claim(self):
        x=self.item();x['multiplier']['value']=2;self.check_no(x,'conflicting')

    def test_single_alternative_transition_conflict(self):
        x=self.item();x['measurement_claims']=[{'key':'transition:13CF5:12D55:box_entry','value':'0.200','unit':'m','status':'supported','provenance':[{'source_id':'rules'}]}]
        self.check_no(x,'conflicting')

    def test_required_assumptions_and_non_design_adjustment(self):
        x=self.item();x['base_path']['assumption_refs']=[];self.check_no(x,'unresolved')
        x=self.item();x['adjustments']['transition']['items'][0]['purpose']='procurement_loss';self.check_no(x,'unresolved')

    def test_invalid_number_and_unit_mismatch(self):
        for value in ['NaN','Infinity',-1,True]:
            x=self.item();x['base_path']['value']=value;self.check_no(x,'unresolved')
        x=self.item();x['adjustments']['transition']['items'][0]['unit']='mm';self.check_no(x)

    def test_explicit_prohibition(self):
        x=self.item();x['measurement_prohibited']=True;self.check_no(x,'blocked')

    def test_source_integrity(self):
        p=ROOT/'quantity-eligibility/fixtures/golden.json'
        bundle=json.loads(p.read_text(encoding='utf-8'))
        for s in bundle['sources']:s['path']=str((p.parent/s['path']).resolve())
        for mode in ('hash','unknown_ref'):
            b=copy.deepcopy(bundle)
            if mode=='hash':b['sources'][0]['sha256']='0'*64
            else:b['objects'][0]['geometry']['provenance']=[{'source_id':'unknown'}]
            with tempfile.TemporaryDirectory() as folder:
                f=Path(folder)/'test.json';f.write_text(json.dumps(b),encoding='utf-8')
                with self.assertRaises(ValueError):load_evidence(f)

    def test_build_plan_keeps_qualification_sources(self):
        plan=resolve_eligibility(self.item())['quantity_formula_plan']
        self.assertTrue(plan['geometry_basis']['provenance'])
        self.assertTrue(plan['height_evidence']['provenance'])
        self.assertTrue(plan['deduplication']['provenance'])
        self.assertFalse(plan['evaluated'])

if __name__=='__main__':unittest.main(verbosity=2)
