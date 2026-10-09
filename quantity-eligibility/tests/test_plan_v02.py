import copy
import sys
import unittest
from decimal import Decimal, localcontext, Inexact, Rounded, ROUND_HALF_EVEN
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'quantity-eligibility'))
from plan_v02 import export_plan, content_hash, seal

def precheck(plan):
    with localcontext() as c:
        c.prec=plan['arithmetic_policy']['precision']
        c.traps[Inexact]=True;c.traps[Rounded]=True
        terms=plan['unit_execution_contract']['components']
        values=[Decimal(t['original_value'])*Decimal(t['conversion']['factor']) for t in terms]
        exact=sum(values,Decimal(0))*Decimal(str(plan['multiplier']['value']))
        c.traps[Inexact]=False;c.traps[Rounded]=False
        reported=exact.quantize(Decimal('1e-'+str(plan['reporting_policy']['decimal_places'])),rounding=ROUND_HALF_EVEN)
        return str(exact),str(reported)

class PlanContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        cls.decisions=json.loads((ROOT/'outputs/quantity-eligibility-v01/golden-results.json').read_text(encoding='utf-8-sig'))
        cls.source_hash=__import__('hashlib').sha256((ROOT/'outputs/quantity-eligibility-v01/golden-results.json').read_bytes()).hexdigest()
        cls.correction=json.loads((ROOT/'outputs/quantity-build-plan-v02/correction-evidence.json').read_text(encoding='utf-8'))
        cls.policy=json.loads((ROOT/'outputs/quantity-build-plan-v02/project-numeric-reporting-policy.json').read_text(encoding='utf-8'))
    def plan(self):return export_plan(self.decisions[0],self.source_hash,self.correction,self.policy)
    def test_both_golden_exact_precheck(self):
        for d in self.decisions:
            p=export_plan(d,self.source_hash,self.correction,self.policy)
            self.assertEqual(precheck(p),('7.77128331912231535912969050917979628','7.771283319'))
            self.assertEqual(str(p['multiplier']['value']),'1')
            self.assertEqual(p['base_path']['value'],'7.47128331912231535912969050917979628')
    def test_self_contained_flags(self):
        p=self.plan()
        for key in ('quantity_formula_ready','generation_allowed','design_net_quantity_generation_allowed'):self.assertIs(p[key],True)
        self.assertEqual(p['approved_semantic_role'],'fire_alarm_bus_segment')
        self.assertEqual(p['deduplication']['evidence_status'],'supported')
        self.assertEqual(p['deduplication']['execution_status'],'passed')
        self.assertEqual(p['deduplication']['status'],'supported')
    def test_correction_and_no_mutation(self):
        before=copy.deepcopy(self.decisions);p=self.plan()
        self.assertEqual(before,self.decisions)
        self.assertNotIn('?',p['binding']['drawing_ref'])
        self.assertTrue(p['corrections_applied']['changed_paths'])
        self.assertEqual(p['corrections_applied']['evidence']['historical_value'],'EX-BX???????????_t8_t3.dwg')
        self.assertEqual(p['unit_execution_contract']['raw_geometry_conversion']['binding']['drawing_ref'],p['binding']['drawing_ref'])
    def test_hash_deterministic(self):
        p=self.plan();self.assertEqual(p,self.plan());self.assertEqual(p['content_hash'],content_hash(p))
    def test_gate_contract_invalid(self):
        for key,value in [('quantity_formula_ready',False),('quantity_eligibility_status','partial'),('design_net_quantity_generation_allowed',False)]:
            d=copy.deepcopy(self.decisions[0]);d[key]=value
            with self.assertRaises(ValueError):export_plan(d,self.source_hash,self.correction,self.policy)
    def test_wrong_correction_scope_or_hash(self):
        for key,value in [('target_object_ids',[]),('source_artifact_sha256','0'*64)]:
            e=copy.deepcopy(self.correction);e[key]=value;seal(e)
            with self.assertRaises(ValueError):export_plan(self.decisions[0],self.source_hash,e,self.policy)
    def test_policy_not_drawing_fact(self):
        p=self.plan()['reporting_policy']
        self.assertFalse(p['is_drawing_fact']);self.assertFalse(p['is_national_standard'])
        self.assertEqual(p['rounding_mode'],'ROUND_HALF_EVEN')
        self.assertEqual(p['intermediate_rounding'],'none')
    def test_dedup_and_units_fail_closed(self):
        d=copy.deepcopy(self.decisions[0]);d['quantity_formula_plan']['deduplication']['status']='partial'
        with self.assertRaises(ValueError):export_plan(d,self.source_hash,self.correction,self.policy)
        d=copy.deepcopy(self.decisions[0]);del d['quantity_formula_plan']['base_path']['unit']
        with self.assertRaises(ValueError):export_plan(d,self.source_hash,self.correction,self.policy)
    def test_all_execution_terms_have_sources(self):
        for t in self.plan()['unit_execution_contract']['components']:
            self.assertTrue(t['provenance']);self.assertEqual(t['conversion']['status'],'approved')
            self.assertEqual(t['dimension'],'length')
    def test_tampered_reporting_policy(self):
        p=copy.deepcopy(self.policy);p['decimal_places']=2
        with self.assertRaises(ValueError):export_plan(self.decisions[0],self.source_hash,self.correction,p)

    def test_schema_required_and_const_contract(self):
        import json
        schema=json.loads((ROOT/'quantity-eligibility/schemas/quantity-build-plan-v02.schema.json').read_text(encoding='utf-8'))
        def check(value,definition):
            if 'const' in definition:self.assertEqual(value,definition['const'])
            if isinstance(value,dict):
                for k in definition.get('required',[]):self.assertIn(k,value)
                for k,s in definition.get('properties',{}).items():
                    if k in value:check(value[k],s)
            if isinstance(value,list) and 'items' in definition:
                for item in value:check(item,definition['items'])
        for d in self.decisions:check(export_plan(d,self.source_hash,self.correction,self.policy),schema)

if __name__=='__main__':unittest.main(verbosity=2)
