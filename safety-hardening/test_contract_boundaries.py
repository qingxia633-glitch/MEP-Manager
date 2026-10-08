"""Additional fail-closed cases, recorded before implementation changes."""
import copy
import unittest
import test_adversarial
from test_adversarial import load
from fixtures import item, plan, seal


class ContractBoundaries(unittest.TestCase):
    def test_placeholder_roles(self):
        eligibility = load('quantity-eligibility')
        builder = load('design-net-quantity', 'builder.py')
        for role in ('unknown', 'unresolved', 'partial', 'conflicting', 'rejected', 'not_evaluated', ' UNKNOWN '):
            with self.subTest(role=role):
                x = item(); x['semantic_gate']['approved_semantic_role'] = role
                self.assertNotEqual(eligibility.resolve_eligibility(x)['quantity_eligibility_status'], 'eligible')
                p = plan(); p['approved_semantic_role'] = role
                self.assertNotEqual(builder.build(seal(p), [])['status'], 'built')

    def test_target_id_contract(self):
        m = load('project-rule-applicability')
        for value in ('E-EXTRA', [], ['E', 'E'], [1], [' E'], None, {}):
            with self.subTest(value=value):
                r, q = test_adversarial.Safety().propagation(); r.pop('propagation_key'); r['target_ids'] = value
                with self.assertRaises(ValueError): m.resolve(r, q)

    def test_native_frozen_hash_tamper(self):
        m = load('design-net-quantity', 'builder.py'); p = plan()
        q = m.build(p, [])['quantity']; q['formula']['owned_adjustments'][0]['device'] = 'tampered'
        self.assertNotEqual(m.replay_validate(p, q)['status'], 'replay_matched')

    def test_metadata_cannot_change_quantity_identity(self):
        m = load('design-net-quantity', 'builder.py'); p = plan(); issued = m.build(p, [])['quantity']
        for key in ('audit_note', 'comment', 'timestamp', 'path'):
            with self.subTest(key=key):
                other = copy.deepcopy(p); other['binding'][key] = 'nonsemantic'
                self.assertEqual(m.build(seal(other), [issued])['status'], 'duplicate_detected')

    def test_builder_rejects_duplicate_physical_adjustment(self):
        m = load('design-net-quantity', 'builder.py'); p = plan()
        p['owned_adjustments'][1].update(device=p['owned_adjustments'][0]['device'], transition_type=p['owned_adjustments'][0]['transition_type'])
        self.assertNotEqual(m.build(seal(p), [])['status'], 'built')


if __name__ == '__main__': unittest.main()
