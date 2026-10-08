"""Explicit S2 migration guards; independent native evidence, no frozen edits."""
import copy
import unittest
from fixtures import plan, seal
from test_adversarial import load


class NativeReplayContract(unittest.TestCase):
    def setUp(self):
        self.builder = load('design-net-quantity', 'builder.py')
        self.plan = plan()
        self.plan['assumptions'] = [{
            'id': 'native-approved-assumption', 'status': 'approved',
            'value': 'synthetic explicit assumption',
            'scope': {'binding': copy.deepcopy(self.plan['binding'])},
            'provenance': [{'source_id': 'synthetic-review'}]}]
        seal(self.plan)
        result = self.builder.build(self.plan, [])
        self.assertEqual(result['status'], 'built')
        self.quantity = result['quantity']

    def test_complete_native_contract_matches(self):
        for field in ('formula', 'provenance', 'assumptions', 'source_evidence_hashes', 'content_hash'):
            self.assertTrue(self.quantity[field])
        self.assertTrue(self.quantity['formula']['owned_adjustments'][0]['owner'])
        result = self.builder.replay_validate(self.plan, self.quantity)
        self.assertEqual(result['status'], 'replay_matched')
        self.assertTrue(result['numeric_match'])
        self.assertTrue(result['evidence_contract_match'])

    def test_same_numbers_changed_owner_not_full_match(self):
        self.plan['owned_adjustments'][0]['owner']['edge_handle'] = 'foreign-edge'
        result = self.builder.replay_validate(seal(self.plan), self.quantity)
        self.assertNotEqual(result['status'], 'replay_matched')

    def test_same_value_changed_provenance_not_full_match(self):
        self.plan['provenance']['synthetic-review']['sha256'] = 'e' * 64
        self.check_numeric_only()

    def test_same_value_changed_assumptions_not_full_match(self):
        self.plan['assumptions'][0]['value'] = 'different approved synthetic assumption'
        self.check_numeric_only()

    def check_numeric_only(self):
        result = self.builder.replay_validate(seal(self.plan), self.quantity)
        self.assertTrue(result['numeric_match'])
        self.assertFalse(result['evidence_contract_match'])
        self.assertEqual(result['status'], 'replay_mismatch')


if __name__ == '__main__':
    unittest.main()
