import copy
import json
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'design-net-quantity'))
from builder import build, replay_validate, seal

def plan(kind='conduit'):
    return json.loads((ROOT / f'outputs/quantity-build-plan-v02/golden-{kind}-v02.json').read_text(encoding='utf-8'))

def synthetic(multiplier=1, unit='m'):
    p = plan()
    p['binding']['edge_handle'] = 'synthetic'
    p['object_id'] = 'synthetic'
    p['corrections_applied'] = {}
    vals = ['10', '0.2', '0.3'] if unit == 'm' else ['10000', '200', '300']
    records = [p['base_path']] + p['owned_adjustments']
    for i, (r, t, v) in enumerate(zip(records, p['unit_execution_contract']['components'], vals)):
        r['value' if i == 0 else 'length'] = v
        r['unit'] = unit
        t.update(original_value=v, original_unit=unit, normalized_value=['10','0.2','0.3'][i])
        t['conversion'].update(source_unit=unit, factor='1' if unit == 'm' else '0.001')
    p['multiplier']['value'] = multiplier
    p['unit_execution_contract']['multiplier'].update(original_value=str(multiplier), normalized_value=str(multiplier))
    return seal(p)

def frozen(kind):
    data = json.loads((ROOT/'outputs/golden-project-measurement-rules-20261004/design-net-quantities.json').read_text(encoding='utf-8-sig'))
    q = data['quantities'][0 if kind == 'conduit' else 1]
    p = plan(kind)
    # Explicit project adapter. No Builder inference from identifiers/spec strings.
    scope=copy.deepcopy(p['binding']); scope['edge_handle']='13CF5'
    return {'scope':scope, 'quantity_kind':kind, 'approved_semantic_role':'fire_alarm_bus_segment',
            'specification':q['spec'], 'installation_method':q['installation'],
            'computed_quantity':{'reported_value':q['value'], 'unit':q['unit']},
            'multiplier':q['countMultiplier'], 'source_id':q['id'],
            'source_artifact':'outputs/golden-project-measurement-rules-20261004/design-net-quantities.json',
            'source_sha256':hashlib.sha256((ROOT/'outputs/golden-project-measurement-rules-20261004/design-net-quantities.json').read_bytes()).hexdigest()}

class BuilderTests(unittest.TestCase):
    def test_conduit_replay(self):
        self.assertEqual(replay_validate(plan(), frozen('conduit'))['status'], 'replay_matched')
    def test_wire_replay(self):
        p=plan('wire'); self.assertEqual(p['multiplier']['value'],1)
        self.assertEqual(replay_validate(p, frozen('wire'))['status'],'replay_matched')
    def test_synthetic(self):
        self.assertEqual(build(synthetic(), [])['quantity']['computed_quantity']['exact_value'],'10.5')
    def test_multiplier(self):
        self.assertEqual(build(synthetic(2), [])['quantity']['computed_quantity']['exact_value'],'21.0')
    def test_mm_conversion(self):
        self.assertEqual(build(synthetic(unit='mm'), [])['quantity']['computed_quantity']['reported_value'],'10.500000000')
    def test_schema(self):
        p=plan(); del p['approved_semantic_role']; seal(p)
        self.assertEqual(build(p,[])['status'],'invalid_plan')
    def test_provenance(self):
        p=plan(); p['base_path']['provenance']=[]; seal(p)
        self.assertEqual(build(p,[])['status'],'contract_violation')
    def test_dedup(self):
        p=plan(); p['deduplication']['execution_status']='pending'; seal(p)
        self.assertNotEqual(build(p,[])['status'],'built')
    def test_blocked_edges(self):
        for edge in ['13CF0','13CE8','13CE9','14147']:
            p=plan(); p['binding']['edge_handle']=edge; p['quantity_eligibility_status']='blocked'; seal(p)
            self.assertEqual(build(p,[])['status'],'blocked')
    def test_duplicate(self):
        self.assertEqual(build(plan(),[frozen('conduit')])['status'],'duplicate_detected')
    def test_registry_required(self):
        self.assertEqual(build(synthetic())['status'],'blocked')
    def test_decimal(self):
        r=replay_validate(plan(),frozen('conduit'))
        self.assertEqual(r['quantity']['computed_quantity']['exact_value'],'7.77128331912231535912969050917979628')
    def test_determinism_no_mutation(self):
        p=synthetic(); before=copy.deepcopy(p)
        self.assertEqual(build(p,[]),build(p,[])); self.assertEqual(p,before)
    def test_correction(self):
        q=replay_validate(plan(),frozen('conduit'))['quantity']
        self.assertEqual(q['scope']['drawing_ref'],plan()['corrections_applied']['evidence']['corrected_value'])
        self.assertTrue(q['correction_evidence_refs'])
    def test_procurement_partial(self):
        p=synthetic(); p['ConduitMaterialRequirement']={'status':'partial'}; seal(p)
        self.assertEqual(build(p,[])['status'],'built')
    def test_mixed_units(self):
        p=synthetic(); p['owned_adjustments'][0]['unit']='mm'; seal(p)
        self.assertEqual(build(p,[])['status'],'contract_violation')
    def test_formula_extra_term(self):
        p=synthetic(); p['formula_components']['arguments'][0]['references'].append('loss'); seal(p)
        self.assertEqual(build(p,[])['status'],'contract_violation')
    def test_hash_tamper(self):
        p=synthetic(); p['multiplier']['value']=5
        self.assertEqual(build(p,[])['status'],'contract_violation')
    def test_conversion_inconsistent(self):
        p=synthetic(); p['unit_execution_contract']['components'][0]['normalized_value']='11'; seal(p)
        self.assertEqual(build(p,[])['status'],'contract_violation')
    def test_replay_mismatch(self):
        f=frozen('conduit'); f['computed_quantity']['reported_value']='8'
        self.assertEqual(replay_validate(plan(),f)['status'],'replay_mismatch')
    def test_rounding_tie(self):
        p=synthetic(); p['reporting_policy']['decimal_places']=0; seal(p['reporting_policy']); seal(p)
        self.assertEqual(build(p,[])['quantity']['computed_quantity']['reported_value'],'10')
    def test_no_intermediate_rounding(self):
        p=synthetic(); p['arithmetic_policy']['precision']=1; seal(p)
        self.assertEqual(build(p,[])['status'],'contract_violation')
    def test_locator_does_not_change_content_hash(self):
        p=synthetic(); first=build(p,[])['quantity']['content_hash']
        p['provenance']['route']['path']='D:/another-machine/route.json'
        p['source_evidence_hashes']['route']['path']='D:/another-machine/route.json'
        seal(p)
        self.assertEqual(first,build(p,[])['quantity']['content_hash'])
    def test_wrong_frozen_scope(self):
        f=frozen('conduit'); f['scope']['edge_handle']='other'
        self.assertEqual(replay_validate(plan(),f)['status'],'replay_mismatch')
    def test_replay_new_object(self):
        p=synthetic(); q=build(p,[])['quantity']
        self.assertEqual(replay_validate(p,q)['status'],'replay_matched')
    def test_full_schema_nested_type(self):
        p=synthetic(); p['reporting_policy']['decimal_places']='9'; seal(p['reporting_policy']);seal(p)
        r=build(p,[])
        self.assertEqual(r['status'],'invalid_plan');self.assertTrue(r['validation_errors'])
    def test_stale_reporting_policy_hash(self):
        p=synthetic(); p['reporting_policy']['decimal_places']=2;seal(p)
        self.assertEqual(build(p,[])['status'],'contract_violation')

if __name__=='__main__': unittest.main()
