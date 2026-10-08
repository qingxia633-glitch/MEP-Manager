import copy
import unittest
from test_adversarial import load
from fixtures import plan, seal


class PlanConsistency(unittest.TestCase):
    def test_audit_binding_cannot_contradict_execution_scope(self):
        m=load('design-net-quantity','builder.py')
        p=plan(); p['unit_execution_contract']['raw_geometry_conversion']['binding']['edge_handle']='foreign'
        self.assertNotEqual(m.build(seal(p),[])['status'],'built')

    def test_owned_adjustment_ids_are_unique(self):
        m=load('design-net-quantity','builder.py'); p=plan()
        p['owned_adjustments'][1]['adjustment_id']=p['owned_adjustments'][0]['adjustment_id']
        self.assertNotEqual(m.build(seal(p),[])['status'],'built')

    def test_native_contract_matching_and_legacy_value_match_are_distinct(self):
        m=load('design-net-quantity','builder.py'); p=plan(); q=m.build(p,[])['quantity']
        native=m.replay_validate(p,q)
        self.assertTrue(native['numeric_match']);self.assertTrue(native['evidence_contract_match'])
        legacy={k:copy.deepcopy(q[k]) for k in ('scope','quantity_kind','approved_semantic_role','specification','installation_method','computed_quantity')}
        legacy['multiplier']=1
        result=m.replay_validate(p,legacy)
        self.assertTrue(result['numeric_match']);self.assertFalse(result['evidence_contract_match'])
        self.assertEqual(result['status'],'replay_value_matched_legacy_evidence_incomplete')

    def test_changed_correction_same_id_is_not_full_replay(self):
        m=load('design-net-quantity','builder.py'); p=plan()
        correction=seal({'correction_id':'synthetic-correction','status':'approved',
                         'target_object_ids':[p['object_id']],'edge_handle':p['binding']['edge_handle'],
                         'corrected_value':p['binding']['drawing_ref'],'basis':'review A'})
        p['corrections_applied']={'evidence':correction,'changed_paths':[]};seal(p)
        q=m.build(p,[])['quantity']
        p['corrections_applied']['evidence']['basis']='review B'
        seal(p['corrections_applied']['evidence']);seal(p)
        r=m.replay_validate(p,q)
        self.assertTrue(r['numeric_match'])
        self.assertFalse(r['evidence_contract_match'])
        self.assertEqual(r['status'],'replay_mismatch')


if __name__=='__main__':unittest.main()
