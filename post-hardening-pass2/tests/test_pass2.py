"""Pass 2 adversarial contracts. Synthetic declarations are not project evidence."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'post-hardening-tests'))
from test_findings import item, plan, seal, load

TOP_LEVEL = ('AcquisitionMode="ModelSpaceTopLevelAllLayers"\n'
             'ModelSpaceTopLevel="included"\nNestedBlocks="not expanded"\n')


def report(owners=('I1',), scope=TOP_LEVEL):
    raw = 'DWG="synthetic.dwg"\n' + scope
    for owner in owners:
        raw += ('EntityHandle="' + owner + '"\nDXF_Type="INSERT"\n'
                'AttributeTag="A"\nAttributeText_RAW="S"\n'
                'Attribute_DXF=((5 . "T") (10 0 0 0))\n')
    return raw


def adapter(raw):
    module = load('project-evidence-discovery', 'discovery.py')
    from annotations import load_report
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / 'synthetic.txt'
        source.write_text(raw, encoding='utf-8')
        context = load_report(source, project_id='synthetic-project')
        return context, module.discover(context)


def planar():
    p = plan()
    p['owned_adjustments'] = []
    p['formula_components']['arguments'][0]['references'] = ['base_path.value']
    p['unit_execution_contract']['components'] = p['unit_execution_contract']['components'][:1]
    p['height_evidence']['status'] = 'not_applicable'
    p['height_evidence']['reason'] = 'Synthetic approved planar-only measurement'
    p['height_requirement'] = 'not_applicable'
    p['height_evidence']['measurement_rule'] = {
        'rule_id': 'synthetic-planar-only/1', 'status': 'approved',
        'binding': copy.deepcopy(p['binding']), 'measurement_mode': 'converted_2d',
        'height_requirement': 'not_applicable', 'provenance': ['synthetic rule declaration']}
    return seal(p)


class Pass2(unittest.TestCase):
    def test_H1_cross_instance_gate_eligibility_builder(self):
        g = load('project-evidence-gate')
        i = dict(project_id='P', drawing_ref='D', parent_path=['I1'], edge_handle='X', scope_type='edge')
        e = dict(evidence_id='E', binding_id='B', evidence_type='human_project_confirmation',
                 evidence_strength='direct_object_binding', status='supported', assertion='affirm',
                 semantic_role='bus', provenance=['synthetic-review'])
        b = dict(i, binding_id='B', review_status='reviewed', evidence_ids=['E'], provenance=['synthetic-review'])
        bundle = dict(project_id='P', drawing_ref='D', evidence=[e], bindings=[b])
        good = g.evaluate_semantics(i, bundle, i)
        self.assertTrue(good['semantic_gate_passed'])
        self.assertEqual(good['accepted_evidence'][0]['object_identity']['parent_path'], ['I1'])
        other = dict(i, parent_path=['I2'])
        bad = g.evaluate_semantics(other, bundle, other)
        self.assertFalse(bad['semantic_gate_passed'])
        x = item(); x['semantic_gate'] = bad
        decision = load('quantity-eligibility').resolve_eligibility(x)
        self.assertFalse(decision['design_net_quantity_generation_allowed'])
        self.assertIsNone(decision['quantity_formula_plan'])
        exporter = load('quantity-eligibility', 'plan_v02.py')
        self.assertRaises(ValueError, exporter.export_plan, decision, 'f' * 64, None, plan()['reporting_policy'])
        p = plan(); p['owned_adjustments'][0]['owner']['parent_path'] = ['I1']
        self.assertEqual(load('design-net-quantity', 'builder.py').build(seal(p), [])['status'], 'contract_violation')

    def test_H1_missing_identity_rejected(self):
        x = item(); del x['semantic_gate']['object_identity']['parent_path']
        self.assertFalse(load('quantity-eligibility').resolve_eligibility(x)['design_net_quantity_generation_allowed'])

    def test_H2_arithmetic_consistent_wrong_mm_factor(self):
        x = item(); x['geometry']['source_unit'] = 'mm'
        x['geometry']['conversion'].update(from_unit='mm', factor='1', converted_length='10')
        r = load('quantity-eligibility').resolve_eligibility(x)
        self.assertIn('unit_conversion_contract_invalid', r['blocking_reasons'])

    def test_H2_physical_and_cad_contracts_separate(self):
        load('quantity-eligibility')
        from unit_contract import conversion_contract
        self.assertEqual(conversion_contract(dict(from_unit='mm', to_unit='m', factor='0.001'), {})['contract_id'], 'engineering-length-units/1')
        self.assertRaises(ValueError, conversion_contract, dict(from_unit='drawing_unit', to_unit='m', factor='0.001'), {})

    def test_H3_missing_geometry(self):
        p = plan(); p['base_path']['mode'] = 'approved_3d'; del p['geometry_basis']
        self.assertEqual(load('design-net-quantity', 'builder.py').build(seal(p), [])['status'], 'contract_violation')

    def test_H3_unresolved_and_foreign_height(self):
        m = load('design-net-quantity', 'builder.py')
        for state in ('unknown', 'unresolved', 'conflicting'):
            p = plan(); p['height_evidence']['status'] = state
            self.assertEqual(m.build(seal(p), [])['status'], 'contract_violation')
        p = plan(); p['height_evidence']['binding']['parent_path'] = ['foreign']
        self.assertEqual(m.build(seal(p), [])['status'], 'contract_violation')

    def test_H3_height_exemption_must_be_explicit(self):
        p = planar(); del p['height_requirement']
        self.assertEqual(load('design-net-quantity', 'builder.py').build(seal(p), [])['status'], 'contract_violation')

    def test_H3_height_exemption_requires_reviewed_rule(self):
        p = planar(); del p['height_evidence']['measurement_rule']
        self.assertEqual(load('design-net-quantity', 'builder.py').build(seal(p), [])['status'], 'contract_violation')

    def test_H3_height_exemption_cannot_override_3d(self):
        p = plan(); p['base_path']['mode'] = 'approved_3d'; p['height_requirement'] = 'not_applicable'
        self.assertEqual(load('design-net-quantity', 'builder.py').build(seal(p), [])['status'], 'contract_violation')

    def test_H3_valid_explicit_planar_rule(self):
        self.assertEqual(load('design-net-quantity', 'builder.py').build(planar(), [])['status'], 'built')

    def test_H3_unreviewed_or_foreign_exemption_rule(self):
        m = load('design-net-quantity', 'builder.py')
        for change in ('status', 'provenance', 'binding'):
            p = planar(); rule = p['height_evidence']['measurement_rule']
            if change == 'status': rule['status'] = 'unresolved'
            elif change == 'provenance': rule['provenance'] = []
            else: rule['binding']['parent_path'] = ['foreign']
            self.assertEqual(m.build(seal(p), [])['status'], 'contract_violation')

    def test_H3_eligibility_cannot_bypass_exemption_rule(self):
        x = item(); p = planar(); x['height'] = copy.deepcopy(p['height_evidence'])
        x['height_requirement'] = 'not_applicable'
        x['adjustments']['transition'].update(items=[], expected_connections=[])
        del x['height']['measurement_rule']
        self.assertFalse(load('quantity-eligibility').resolve_eligibility(x)['design_net_quantity_generation_allowed'])

    def test_H3_eligibility_carries_exemption(self):
        x = item(); p = planar(); x['height'] = copy.deepcopy(p['height_evidence'])
        x['height_requirement'] = 'not_applicable'
        group = x['adjustments']['transition']; group['items'] = []; group['expected_connections'] = []
        r = load('quantity-eligibility').resolve_eligibility(x)
        self.assertEqual(r['quantity_eligibility_status'], 'eligible')
        self.assertEqual(r['quantity_formula_plan']['height_requirement'], 'not_applicable')

    def test_H4_changed_spec_provenance_same_value(self):
        m = load('design-net-quantity', 'builder.py'); p = plan(); q = m.build(p, [])['quantity']
        p['specification']['provenance'] = ['different synthetic review']
        r = m.replay_validate(seal(p), q)
        self.assertTrue(r['numeric_match']); self.assertFalse(r['evidence_contract_match'])

    def test_H4_semantic_binding_review_must_be_frozen(self):
        m = load('design-net-quantity', 'builder.py'); p = plan()
        p['semantic_gate'] = copy.deepcopy(item()['semantic_gate'])
        q = m.build(seal(p), [])['quantity']
        p['semantic_gate']['accepted_evidence'][0]['provenance'] = ['changed semantic review']
        r = m.replay_validate(seal(p), q)
        self.assertTrue(r['numeric_match']); self.assertFalse(r['evidence_contract_match'])

    def test_H4_native_complete_positive(self):
        m = load('design-net-quantity', 'builder.py'); p = plan(); q = m.build(p, [])['quantity']
        self.assertEqual(m.replay_validate(p, q)['status'], 'replay_matched')

    def test_H4_eligibility_export_retains_semantic_review(self):
        decision = load('quantity-eligibility').resolve_eligibility(item())
        module = load('quantity-eligibility', 'plan_v02.py')
        p = module.export_plan(decision, 'e' * 64, None, plan()['reporting_policy'])
        self.assertEqual(p['semantic_gate'], decision['semantic_gate'])
        m = load('design-net-quantity', 'builder.py')
        q = m.build(p, [])['quantity']
        self.assertEqual(q['evidence_contract']['records']['semantic_gate'], decision['semantic_gate'])

    def test_H4_exemption_rule_change_not_full_replay(self):
        m = load('design-net-quantity', 'builder.py'); p = planar(); q = m.build(p, [])['quantity']
        p['height_evidence']['measurement_rule']['provenance'] = ['different reviewed exemption']
        r = m.replay_validate(seal(p), q)
        self.assertTrue(r['numeric_match']); self.assertFalse(r['evidence_contract_match'])

    def test_N1_full_adapter_owner_fields(self):
        c, r = adapter(report())
        a = c['annotations'][0]
        self.assertEqual(a['attribute_handle'], 'T')
        self.assertEqual(a['attribute_parent_path'], ['I1'])
        self.assertEqual(a['owner_insert_handle'], 'I1')
        self.assertEqual(a['owner_parent_path'], [])
        self.assertEqual(r['bindings'][0]['target_id'], 'I1')
        self.assertEqual(r['bindings'][0]['binding_status'], 'supported')

    def test_N1_missing_scope_not_modelspace(self):
        c, r = adapter(report(scope=''))
        self.assertFalse(r['bindings'])
        self.assertIn('insert_parent_scope_not_established:I1', c['extraction_gaps'])

    def test_N1_nested_scope_not_modelspace(self):
        c, r = adapter(report(scope='AcquisitionMode="NestedBlockDefinition"\n'))
        self.assertFalse(r['bindings'])

    def test_N1_unknown_owner_retains_raw_without_fabricated_path(self):
        c, r = adapter(report(scope=''))
        a = c['unresolved_attributes'][0]
        self.assertEqual(a['attribute_handle'], 'T')
        self.assertEqual(a['owner_insert_handle'], 'I1')
        self.assertIsNone(a['owner_parent_path'])
        self.assertEqual(a['raw_text'], 'S')
        self.assertEqual(a['association_status'], 'unresolved')

    def test_N1_contradictory_nested_acquisition_not_top_level(self):
        c, r = adapter(report(scope=TOP_LEVEL.replace('not expanded', 'expanded')))
        self.assertFalse(r['bindings'])

    def test_N1_repeated_attribute_handles_not_crossed(self):
        c, r = adapter(report(('I1', 'I2')))
        self.assertEqual({b['target_id'] for b in r['bindings']}, {'I1', 'I2'})
        self.assertEqual({tuple(a['attribute_parent_path']) for a in c['annotations']}, {('I1',), ('I2',)})


if __name__ == '__main__':
    unittest.main(verbosity=2)
