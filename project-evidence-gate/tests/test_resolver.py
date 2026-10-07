import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'project-evidence-gate'))
from resolver import evaluate_semantics
from evidence import load_bundle
from evidence import DIRECT_TYPES

def candidate(role='alarm_or_linkage_bus'):
    return {'edge_handle': 'E', 'candidate_role': role, 'candidate_confidence': 'medium',
            'project_specific_status': 'not_evaluated', 'design_net_quantity_eligible': False}

def evidence(role='fire_alarm_bus_segment', id='D'):
    return {'evidence_id': id, 'evidence_type': 'human_project_confirmation',
            'evidence_strength': 'direct_object_binding', 'status': 'supported',
            'semantic_role': role, 'assertion': 'affirm', 'binding_id': 'B',
            'provenance': [{'source': 'synthetic reviewed project confirmation'}]}

def bundle(records=None):
    return {'project_id': 'P', 'drawing_ref': 'drawing.dwg', 'evidence': records or [],
            'bindings': [{'binding_id': 'B', 'review_status': 'reviewed', 'project_id': 'P',
                          'drawing_ref': 'drawing.dwg', 'edge_handle': 'E',
                          'evidence_ids': [r['evidence_id'] for r in records or []],
                          'provenance': ['synthetic edge-bound review']}], 'provenance': []}

def run(c=None, records=None, b=None):
    return evaluate_semantics(c or candidate(), b or bundle(records), {'project_id': 'P','drawing_ref':'drawing.dwg'})

class Gates(unittest.TestCase):
    def test_direct_human_and_quantity_isolation(self):
        r = run(records=[evidence()])
        self.assertEqual(r['project_specific_status'], 'supported')
        self.assertTrue(r['semantic_gate_passed'])
        self.assertTrue(r['design_net_quantity_eligible'])
        self.assertEqual(r['quantity_eligibility_status'], 'not_evaluated')
        self.assertFalse(r['quantity_generated'])
        self.assertNotIn('length', r)

    def test_no_direct_and_rule_b(self):
        for role in ['alarm_or_linkage_bus','bus_or_module_box_feed','control_or_feedback']:
            c=candidate(role); c['candidate_confidence']='high'
            c['rule_validation_status']='insufficient_project_local_evidence'
            r=run(c)
            self.assertEqual(r['project_specific_status'],'partial')
            self.assertFalse(r['semantic_gate_passed'])

    def test_direct_overrides_and_ignores_rule_maturity(self):
        c=candidate(); c['rule_validation_status']='insufficient_project_local_evidence'
        r=run(c, [evidence('control_or_feedback')])
        self.assertEqual(r['approved_semantic_role'],'control_or_feedback')
        self.assertTrue(r['candidate_overridden'])
        self.assertEqual(r['project_specific_status'],'supported')
        self.assertTrue(r['conflicting_evidence'])

    def test_peer_direct_conflict(self):
        r=run(records=[evidence(),evidence('control_or_feedback','D2')])
        self.assertEqual(r['project_specific_status'],'conflicting')
        self.assertFalse(r['design_net_quantity_eligible'])

    def test_pending_direct_blocks_positive(self):
        for status in ['partial','unresolved','conflicting','invalid']:
            e=evidence(id='D2');e['status']=status
            r=run(records=[evidence(),e])
            self.assertFalse(r['semantic_gate_passed'])
            self.assertNotEqual(r['project_specific_status'],'supported')

    def test_weak_sources_cannot_be_laundered(self):
        for typ in ['manufacturer_generic','online_generic','layer_only','specification_only','nearby_text','pattern_sample','candidate_confidence']:
            e=evidence();e['evidence_type']=typ
            r=run(records=[e])
            self.assertFalse(r['semantic_gate_passed'])
            self.assertEqual(r['project_specific_status'],'partial')

    def test_weak_strengths(self):
        for strength in ['pattern_only','contextual_only','external_generic']:
            e=evidence();e['evidence_strength']=strength
            self.assertFalse(run(records=[e])['semantic_gate_passed'])

    def test_binding_identity_and_review(self):
        for field,value in [('edge_handle','OTHER'),('project_id','OTHER'),('drawing_ref','OTHER'),('review_status','pending'),('evidence_ids',[])]:
            b=bundle([evidence()]);b['bindings'][0][field]=value
            self.assertFalse(run(b=b)['semantic_gate_passed'])

    def test_segment_binding_does_not_expand(self):
        b=bundle([evidence()]);b['bindings'][0]['segment_id']='part-1'
        self.assertFalse(run(b=b)['semantic_gate_passed'])
        c=candidate();c['segment_id']='part-1'
        self.assertTrue(run(c,b=b)['semantic_gate_passed'])

    def test_unknown_and_missing_binding(self):
        self.assertEqual(run(candidate('unknown'))['project_specific_status'],'unresolved')
        b=bundle([evidence()]);b['bindings']=[]
        self.assertFalse(run(b=b)['semantic_gate_passed'])

    def test_direct_negative_is_semantic_only(self):
        e=evidence('alarm_or_linkage_bus');e['assertion']='deny'
        r=run(records=[e])
        self.assertEqual(r['project_specific_status'],'rejected')
        self.assertFalse(r['semantic_gate_passed'])
        self.assertIsNone(r['approved_semantic_role'])

    def test_unrelated_denial_and_positive_denial_conflict(self):
        e=evidence('another_role');e['assertion']='deny'
        self.assertNotEqual(run(records=[e])['project_specific_status'],'rejected')
        e['semantic_role']='fire_alarm_bus_segment'
        self.assertEqual(run(records=[evidence(),dict(e,evidence_id='D2')])['project_specific_status'],'conflicting')

    def test_no_mutation_and_preserved_provenance(self):
        c=candidate();b=bundle([evidence()]);before=copy.deepcopy((c,b))
        r=run(c,b=b)
        self.assertEqual((c,b),before)
        self.assertEqual(r['provenance']['candidate'],c)
        self.assertEqual(r['accepted_evidence'][0]['provenance'],b['evidence'][0]['provenance'])

    def test_duplicate_ids_fail_closed(self):
        self.assertFalse(run(records=[evidence(),evidence()])['semantic_gate_passed'])

    def test_direct_can_resolve_unknown_candidate(self):
        self.assertTrue(run(candidate('unknown'),[evidence()])['semantic_gate_passed'])

    def test_all_direct_types_and_strengths(self):
        for typ,strengths in DIRECT_TYPES.items():
            for strength in strengths:
                e=evidence();e.update(evidence_type=typ,evidence_strength=strength)
                self.assertTrue(run(records=[e])['semantic_gate_passed'])

    def test_incomplete_direct_alone_and_weak_cannot_conflict(self):
        e=evidence();e['status']='unresolved'
        self.assertEqual(run(records=[e])['project_specific_status'],'unresolved')
        e=evidence('control_or_feedback','D2');e['evidence_type']='manufacturer_generic'
        self.assertTrue(run(records=[evidence(),e])['semantic_gate_passed'])

    def test_same_role_multiple_sources_and_ambiguous_candidate(self):
        c=candidate();c['candidate_status']='ambiguous';c['candidate_role']='unknown'
        r=run(c,[evidence(),evidence(id='D2')])
        self.assertTrue(r['semantic_gate_passed'])
        self.assertEqual(len(r['accepted_evidence']),2)

class Project(unittest.TestCase):
    def test_source_hash_and_assertion_guard(self):
        p=ROOT/'project-evidence-gate/project-evidence/garage-golden.json'
        config=json.loads(p.read_text(encoding='utf-8'))
        for s in config['sources']:s['path']=str((p.parent/s['path']).resolve())
        for mode in ['hash','assertion','unknown_source']:
            b=copy.deepcopy(config)
            if mode=='hash':b['sources'][0]['sha256']='0'*64
            elif mode=='assertion':b['sources'][0]['assertions'][0]['expected']='wrong'
            else:b['evidence'][0]['source_ids']=['missing']
            with tempfile.TemporaryDirectory() as folder:
                f=Path(folder)/'bundle.json';f.write_text(json.dumps(b),encoding='utf-8')
                with self.assertRaises(ValueError):load_bundle(f)

    def test_golden_and_four_unapproved_edges(self):
        b=load_bundle(ROOT/'project-evidence-gate/project-evidence/garage-golden.json')
        context={'project_id':b['project_id'],'drawing_ref':b['drawing_ref']}
        r=evaluate_semantics({'edge_handle':'13CF5','candidate_role':'unknown','candidate_confidence':'unknown'},b,context)
        self.assertEqual(r['approved_semantic_role'],'fire_alarm_bus_segment')
        self.assertTrue(r['semantic_gate_passed'])
        fixtures=json.loads((ROOT/'outputs/candidate-semantic-resolver-v01/fixture-results.json').read_text(encoding='utf-8-sig'))
        for c in fixtures[:4]:
            r=evaluate_semantics(c,b,context)
            self.assertEqual(r['project_specific_status'],'partial')
            self.assertFalse(r['semantic_gate_passed'])

if __name__=='__main__':unittest.main(verbosity=2)
