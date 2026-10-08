"""Builder-direct adversaries. All declarations here are synthetic, not project facts."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'post-hardening-tests'))
from test_findings import item, plan as legacy_plan, seal, load


def complete_plan():
    p = legacy_plan()
    p['semantic_gate'] = copy.deepcopy(item()['semantic_gate'])
    # Independent records: mutating accepted evidence must not also mutate Gate identity.
    p['semantic_gate']['accepted_evidence'][0]['object_identity'] = copy.deepcopy(p['semantic_gate']['object_identity'])
    p['semantic_gate']['accepted_evidence'][0].update(status='supported', assertion='affirm',
        semantic_role=p['approved_semantic_role'])
    p['height_requirement'] = 'required'
    p['unit_conversion_contract'] = dict(contract_id='engineering-length-units/1', version='1',
        kind='engineering_units', source_unit='m', target_unit='m', factor='1')
    p['schema_version'] = '0.3'
    return seal(p)


class Admission(unittest.TestCase):
    def reject(self, p):
        r = load('design-net-quantity', 'builder.py').build(seal(p), [])
        self.assertIn(r['status'], ('contract_violation', 'blocked', 'invalid_plan'), r)
        self.assertNotIn('quantity', r)

    def test_complete_native_positive(self):
        m = load('design-net-quantity', 'builder.py'); p = complete_plan()
        r = m.build(p, [])
        self.assertEqual(r['status'], 'built', r)
        self.assertEqual(r['quantity']['computed_quantity']['exact_value'], '10.5')
        self.assertEqual(m.replay_validate(p, r['quantity'])['status'], 'replay_matched')

    def test_gate_missing(self):
        p = complete_plan(); del p['semantic_gate']; self.reject(p)

    def test_gate_conflicting(self):
        p = complete_plan(); p['semantic_gate']['project_specific_status'] = 'conflicting'; self.reject(p)

    def test_gate_failed(self):
        p = complete_plan(); p['semantic_gate']['semantic_gate_passed'] = False; self.reject(p)

    def test_gate_eligibility_false(self):
        p = complete_plan(); p['semantic_gate']['design_net_quantity_eligible'] = False; self.reject(p)

    def test_gate_role_mismatch(self):
        p = complete_plan(); p['semantic_gate']['approved_semantic_role'] = 'another'; self.reject(p)

    def test_gate_foreign_identity(self):
        for field, value in [('parent_path', ['I2']), ('project_id', 'foreign'), ('drawing_ref', 'foreign'), ('edge_handle', 'foreign'), ('segment_id', 'part')]:
            with self.subTest(field=field):
                p = complete_plan(); p['semantic_gate']['object_identity'][field] = value; self.reject(p)

    def test_gate_accepted_identity(self):
        p = complete_plan(); p['semantic_gate']['accepted_evidence'][0]['object_identity']['parent_path'] = ['I2']; self.reject(p)

    def test_gate_context_identity(self):
        p = complete_plan(); p['semantic_gate']['provenance']['context']['drawing_ref'] = 'foreign'; self.reject(p)

    def test_gate_empty_evidence(self):
        p = complete_plan(); p['semantic_gate']['accepted_evidence'] = []; self.reject(p)

    def test_approved_binding_foreign(self):
        p = complete_plan(); p['approved_semantic_binding'] = dict(p['binding'], parent_path=['I2']); self.reject(p)

    def test_wrong_self_consistent_physical_factor(self):
        p = complete_plan(); g = p['geometry_basis']; g['source_unit'] = 'mm'
        g['conversion'].update(from_unit='mm', factor='1', converted_length='10')
        p['unit_execution_contract']['raw_geometry_conversion'] = copy.deepcopy(g['conversion'])
        p['unit_conversion_contract'].update(source_unit='mm', factor='1'); self.reject(p)

    def test_conversion_missing(self):
        p = complete_plan(); del p['geometry_basis']['conversion']; self.reject(p)

    def test_execution_raw_conversion_missing(self):
        p = complete_plan(); p['unit_execution_contract']['raw_geometry_conversion'] = None; self.reject(p)

    def test_base_and_execution_tampered_together(self):
        p = complete_plan(); p['base_path']['value'] = '20'
        p['unit_execution_contract']['components'][0].update(original_value='20', normalized_value='20'); self.reject(p)

    def test_conversion_source_target_mismatch(self):
        for key in ('from_unit', 'to_unit'):
            p = complete_plan(); p['geometry_basis']['conversion'][key] = 'mm'; self.reject(p)

    def test_right_factor_wrong_result(self):
        p = complete_plan(); p['geometry_basis']['conversion']['converted_length'] = '11'; self.reject(p)

    def test_right_result_wrong_factor(self):
        p = complete_plan(); p['geometry_basis']['conversion']['factor'] = '2'; self.reject(p)

    def test_height_missing_assumption(self):
        p = complete_plan(); p['height_evidence'].update(assumptions_required=True, assumption_refs=['missing']); self.reject(p)

    def test_height_foreign_assumption(self):
        p = complete_plan(); p['height_evidence'].update(assumptions_required=True, assumption_refs=['a'])
        p['assumptions'] = [dict(id='a', status='approved', value='x', provenance=['synthetic'],
            scope=dict(binding=dict(p['binding'], parent_path=['I2']), conditions={'slab': 300}))]; self.reject(p)

    def test_assumption_conditions_unsatisfied(self):
        p = complete_plan(); p['height_evidence'].update(assumption_refs=['a'], conditions={'slab': 250})
        p['assumptions'] = [dict(id='a', status='approved', value='x', provenance=['synthetic'],
            scope=dict(binding=copy.deepcopy(p['binding']), conditions={'slab': 300}))]; self.reject(p)

    def test_nested_semantic_assumption_missing(self):
        p = complete_plan(); p['semantic_gate']['accepted_evidence'][0].update(assumptions_required=True, assumption_refs=['absent']); self.reject(p)

    def test_source_evidence_metadata_assumption_missing(self):
        for field in ('provenance', 'source_evidence_hashes'):
            p = complete_plan(); p[field]['synthetic-review'].update(assumptions_required=True, assumption_refs=['absent']); self.reject(p)

    def test_every_registered_evidence_rejects_missing_refs(self):
        fields = ('base_path', 'multiplier', 'specification', 'deduplication', 'geometry_basis',
                  'height_evidence', 'unit_conversion_contract', 'unit_execution_contract', 'reporting_policy')
        for field in fields:
            with self.subTest(field=field):
                p = complete_plan(); p[field].update(assumptions_required=True, assumption_refs=['absent'])
                if field == 'reporting_policy': seal(p[field])
                self.reject(p)
        p = complete_plan(); p['owned_adjustments'][0].update(assumptions_required=True, assumption_refs=[]); self.reject(p)

    def test_nested_exemption_rule_refs_checked(self):
        p = complete_plan(); p['height_evidence']['measurement_rule'] = dict(assumptions_required=True, assumption_refs=['absent']); self.reject(p)

    def test_assumption_unapproved_or_unsourced(self):
        for key, value in [('status', 'unresolved'), ('provenance', [])]:
            p = self.assumed_plan(); p['assumptions'][0][key] = value; self.reject(p)

    @staticmethod
    def assumed_plan():
        p = complete_plan(); p['height_evidence'].update(assumptions_required=True, assumption_refs=['a'], conditions={'slab': 300})
        p['assumptions'] = [dict(id='a', status='approved', value='synthetic', provenance=['synthetic'],
            scope=dict(binding=copy.deepcopy(p['binding']), conditions={'slab': 300}))]
        return p

    def test_positive_height_assumption(self):
        r = load('design-net-quantity', 'builder.py').build(seal(self.assumed_plan()), [])
        self.assertEqual(r['status'], 'built', r)

    def test_assumption_conditions_cannot_use_boolean_as_integer(self):
        p = self.assumed_plan(); p['assumptions'][0]['scope']['conditions'] = {'slab': 1}
        p['height_evidence']['conditions'] = {'slab': True}; self.reject(p)

    def test_nested_assumption_condition_cannot_use_boolean_as_integer(self):
        p = self.assumed_plan(); p['assumptions'][0]['scope']['conditions'] = {'slab': {'value': 1}}
        p['height_evidence']['conditions'] = {'slab': {'value': True}}; self.reject(p)

    def test_assumption_conditions_missing(self):
        p = self.assumed_plan(); del p['height_evidence']['conditions']; self.reject(p)

    def test_assumption_positive_change_replay_mismatch(self):
        p = seal(self.assumed_plan()); m = load('design-net-quantity', 'builder.py'); q = m.build(p, [])['quantity']
        p['assumptions'][0]['provenance'] = ['another approved synthetic source']
        r = m.replay_validate(seal(p), q); self.assertTrue(r['numeric_match']); self.assertFalse(r['evidence_contract_match'])

    def test_positive_exact_mm_conversion(self):
        p = complete_plan(); g = p['geometry_basis']; g.update(base_length='10000', source_unit='mm')
        g['conversion'].update(from_unit='mm', factor='0.001')
        p['unit_conversion_contract'].update(source_unit='mm', factor='0.001')
        p['unit_execution_contract']['raw_geometry_conversion'] = copy.deepcopy(g['conversion'])
        r = load('design-net-quantity', 'builder.py').build(seal(p), [])
        self.assertEqual(r['status'], 'built', r)

    def test_positive_mm_execution_to_m(self):
        p = complete_plan(); g = p['geometry_basis']; g.update(base_length='10000', source_unit='mm', engineering_unit='mm')
        g['conversion'].update(from_unit='mm', to_unit='mm', converted_length='10000')
        p['unit_conversion_contract'].update(source_unit='mm', target_unit='mm')
        p['unit_execution_contract']['raw_geometry_conversion'] = copy.deepcopy(g['conversion'])
        for index, r in enumerate([p['base_path']] + p['owned_adjustments']):
            r['unit'] = 'mm'; value = ['10000', '200', '300'][index]; r['value' if index == 0 else 'length'] = value
            term = p['unit_execution_contract']['components'][index]
            term.update(original_value=value, original_unit='mm')
            term['conversion'].update(source_unit='mm', factor='0.001')
        r = load('design-net-quantity', 'builder.py').build(seal(p), [])
        self.assertEqual(r['status'], 'built', r)
        self.assertEqual(r['quantity']['computed_quantity']['reported_value'], '10.500000000')

    def test_unsupported_raw_float_nan_negative(self):
        for value in (float('nan'), -1, True, 'NaN', 'Infinity'):
            p = complete_plan(); p['geometry_basis']['base_length'] = value
            if isinstance(value, float):
                # Hash itself rejects NaN: no quantity may be produced at this boundary.
                self.assertRaises(ValueError, load('design-net-quantity', 'builder.py').seal, p)
            else: self.reject(p)

    def test_cad_scale_requires_separate_review(self):
        p = complete_plan(); g = p['geometry_basis']; g['source_unit'] = 'drawing_unit'
        g['conversion'].update(from_unit='drawing_unit', conversion_kind='cad_geometry_scale')
        p['unit_execution_contract']['raw_geometry_conversion'] = copy.deepcopy(g['conversion']); self.reject(p)

    def test_positive_separate_cad_scale_and_foreign_scale_rejected(self):
        p = complete_plan(); g = p['geometry_basis']; g.update(base_length='10000', source_unit='drawing_unit')
        contract = seal(dict(contract_id='synthetic-reviewed-scale', version='1', kind='cad_geometry_scale',
            status='approved', binding=copy.deepcopy(p['binding']), provenance=['synthetic scale review'],
            source_unit='drawing_unit', target_unit='m', factor='0.001'))
        g['conversion'].update(from_unit='drawing_unit', factor='0.001', conversion_kind='cad_geometry_scale',
                               reviewed_scale_contract=copy.deepcopy(contract))
        p['unit_conversion_contract'] = copy.deepcopy(contract)
        p['unit_execution_contract']['raw_geometry_conversion'] = copy.deepcopy(g['conversion'])
        m = load('design-net-quantity', 'builder.py')
        self.assertEqual(m.build(seal(p), [])['status'], 'built')
        g['conversion']['reviewed_scale_contract']['binding']['parent_path'] = ['foreign']
        seal(g['conversion']['reviewed_scale_contract']); self.reject(p)

    def test_decimal_conversion_independent_of_caller_context(self):
        from decimal import localcontext
        p = complete_plan(); m = load('design-net-quantity', 'builder.py')
        with localcontext() as context:
            context.prec = 1
            result = m.build(p, [])
        self.assertEqual(result['status'], 'built', result)

    def test_all_gate_identity_fields_and_missing_path_fail_closed(self):
        for container in ('object_identity', 'context', 'accepted'):
            for field in ('project_id', 'drawing_ref', 'parent_path', 'edge_handle', 'scope_type'):
                with self.subTest(container=container, field=field):
                    p = complete_plan(); gate = p['semantic_gate']
                    record = gate['object_identity'] if container == 'object_identity' else gate['provenance']['context'] if container == 'context' else gate['accepted_evidence'][0]['object_identity']
                    del record[field]; self.reject(p)

    def test_approved_3d_does_not_allow_zero_base_path(self):
        p = complete_plan(); p['base_path'].update(mode='approved_3d', value='0')
        p['unit_execution_contract']['components'][0].update(original_value='0', normalized_value='0'); self.reject(p)

    def test_gate_evidence_status_not_defaulted(self):
        p = complete_plan(); del p['semantic_gate']['accepted_evidence'][0]['status']; self.reject(p)

    def test_gate_conflict_cannot_hide_behind_supported(self):
        p = complete_plan(); p['semantic_gate']['conflicting_evidence'] = [{'reason': 'unresolved peer disagreement'}]; self.reject(p)

    def test_legacy_version_cannot_execute(self):
        p = complete_plan(); p['schema_version'] = '0.2'
        r = load('design-net-quantity', 'builder.py').build(seal(p), [])
        self.assertEqual(r['status'], 'blocked'); self.assertIn('legacy_incomplete', r['blocking_reasons'][0])

    def test_exporter_independently_calls_shared_contract(self):
        x = item(); x['height_requirement'] = 'required'; x['semantic_gate'] = copy.deepcopy(complete_plan()['semantic_gate'])
        d = load('quantity-eligibility').resolve_eligibility(x)
        self.assertEqual(d['quantity_eligibility_status'], 'eligible')
        exporter = load('quantity-eligibility', 'plan_v03.py')
        p = exporter.export_plan(d, 'f' * 64, None, complete_plan()['reporting_policy'])
        self.assertEqual(p['schema_version'], '0.3')
        d['quantity_formula_plan']['semantic_gate']['semantic_gate_passed'] = False
        self.assertRaises(ValueError, exporter.export_plan, d, 'f' * 64, None, complete_plan()['reporting_policy'])

    def test_exporter_top_level_gate_cannot_disagree_with_plan(self):
        x = item(); x['height_requirement'] = 'required'; x['semantic_gate'] = copy.deepcopy(complete_plan()['semantic_gate'])
        d = load('quantity-eligibility').resolve_eligibility(x)
        d['semantic_gate']['semantic_gate_passed'] = False
        self.assertRaises(ValueError, load('quantity-eligibility', 'plan_v03.py').export_plan,
                          d, 'f' * 64, None, complete_plan()['reporting_policy'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
