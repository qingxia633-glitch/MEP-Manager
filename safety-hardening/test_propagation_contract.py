import copy
import unittest
from test_adversarial import load
import test_adversarial


class PropagationContract(unittest.TestCase):
    def proven(self):
        r, q = test_adversarial.Safety().propagation()
        p = q['propagation_sources'][0]
        p['root_target'] = dict(id='root', kind='edge', status='supported', provenance=['root review'])
        p['propagation_relation'] = dict(value='explicit group', status='supported', provenance=['relation review'])
        p['propagation_boundary'] = dict(value='closed set', status='supported', provenance=['boundary review'])
        p['termination_condition'] = dict(value='outside set stops', status='supported', provenance=['termination review'])
        return r, q

    def test_proven_components_allow(self):
        r, q = self.proven()
        self.assertTrue(load('project-rule-applicability').resolve(r,q)['may_submit_to_project_gate'])

    def test_each_required_component_is_not_truthiness(self):
        m = load('project-rule-applicability')
        for field in ('root_target','propagation_relation','propagation_boundary','termination_condition'):
            for state in ('unknown','unresolved','partial','conflicting'):
                with self.subTest(field=field,state=state):
                    r, q = self.proven(); q['propagation_sources'][0][field]['status'] = state
                    self.assertFalse(m.resolve(r,q)['may_submit_to_project_gate'])

    def test_missing_component_provenance_blocks(self):
        m = load('project-rule-applicability')
        for field in ('root_target','propagation_relation','propagation_boundary','termination_condition'):
            with self.subTest(field=field):
                r, q = self.proven(); q['propagation_sources'][0][field]['provenance'] = []
                self.assertFalse(m.resolve(r,q)['may_submit_to_project_gate'])

    def test_agreeing_independent_witnesses_are_not_conflict(self):
        r,q=self.proven(); other=copy.deepcopy(q['propagation_sources'][0])
        for field in ('root_target','propagation_relation','propagation_boundary','termination_condition'):
            other[field]['provenance']=['second independent review']
        q['propagation_sources'].append(other)
        self.assertTrue(load('project-rule-applicability').resolve(r,q)['may_submit_to_project_gate'])


if __name__ == '__main__': unittest.main()
