import copy
import json
import sys
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'candidate-semantic'))
from rules import load_rules
from resolver import resolve_candidate

CONFIG = ROOT / 'candidate-semantic/project-rules/garage-fire-alarm.json'

def endpoint(handle, role, role_status='supported', geometry='supported'):
    return {'geometry_connection': {'edge_handle': 'E', 'target_handle': handle,
            'evidence_identity':{'project_id':'current garage fire-alarm project','drawing_ref':'synthetic.dwg','edge_parent_path':[],'target_parent_path':[]},
            'geometric_connection_status': geometry},
            'device_role': {'device_handle': handle, 'canonical_role': role, 'role_status': role_status,
                'evidence_identity':{'project_id':'current garage fire-alarm project','drawing_ref':'synthetic.dwg','parent_path':[]}}}

def sample(a='smoke_detector', b='input_output_module'):
    return {'edge_handle': 'E', 'scope': {'project': 'current garage fire-alarm project', 'validation_area': 'compartment 1'},
            'evidence_identity':{'project_id':'current garage fire-alarm project','drawing_ref':'synthetic.dwg','parent_path':[]},
            'endpoint_A': endpoint('A', a), 'endpoint_B': endpoint('B', b),
            'edge_metadata': {'layer': 'WIRE-消防控制', 'specification_evidence': ['WDZN-RYJS'], 'nearby_text': ['M2']}}

class Gates(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rules = load_rules(CONFIG)

    def run_sample(self, item): return resolve_candidate(item, self.rules)

    def test_a_and_reverse(self):
        a = self.run_sample(sample()); b = self.run_sample(sample('input_output_module', 'smoke_detector'))
        self.assertEqual(a['candidate_role'], 'alarm_or_linkage_bus')
        self.assertEqual(a['candidate_role'], b['candidate_role'])
        self.assertEqual(a['candidate_confidence'], 'medium')
        self.assertEqual(a['rule_validation_status'], 'partial_pattern_support')

    def test_b_pending(self):
        r = self.run_sample(sample('input_output_module', 'fire_damper'))
        self.assertEqual(r['candidate_role'], 'control_or_feedback')
        self.assertEqual(r['candidate_confidence'], 'low')
        self.assertEqual(r['rule_validation_status'], 'insufficient_project_local_evidence')

    def test_c(self):
        self.assertEqual(self.run_sample(sample('input_output_module', 'module_box'))['candidate_role'], 'bus_or_module_box_feed')

    def test_context_cannot_classify(self):
        r = self.run_sample(sample('unknown', 'unknown'))
        self.assertEqual(r['candidate_role'], 'unknown')
        self.assertEqual(r['candidate_confidence'], 'unknown')

    def test_geometry_blockers(self):
        for status in ['unresolved', 'rejected', 'invalid', None]:
            s = sample('input_output_module', 'fire_damper')
            s['endpoint_B']['geometry_connection']['geometric_connection_status'] = status
            r = self.run_sample(s)
            self.assertEqual(r['candidate_role'], 'unknown')
            self.assertEqual(r['matched_rules'], [])
            self.assertTrue(r['limiting_evidence'])

    def test_partial_geometry(self):
        s = sample(); s['endpoint_B']['geometry_connection']['geometric_connection_status'] = 'partial'
        r = self.run_sample(s)
        self.assertEqual(r['candidate_status'], 'partial')
        self.assertEqual(r['candidate_confidence'], 'unknown')
        self.assertIn('geometry_blocker', str(r['limiting_evidence']))

    def test_role_blockers(self):
        for status in ['partial', 'unresolved', 'conflicting', 'explicit', None]:
            s = sample(); s['endpoint_A']['device_role']['role_status'] = status
            r = self.run_sample(s)
            self.assertEqual(r['candidate_status'], 'unresolved')
            self.assertEqual(r['candidate_role'], 'unknown')

    def test_inherited_downgrades(self):
        s = sample(); s['endpoint_A']['device_role']['role_status'] = 'inherited'
        r = self.run_sample(s)
        self.assertEqual(r['candidate_role'], 'alarm_or_linkage_bus')
        self.assertEqual(r['candidate_confidence'], 'low')
        self.assertEqual(r['endpoint_A']['role_status'], 'inherited')

    def test_identity_mismatch(self):
        for field, value in [('edge_handle', 'OTHER'), ('target_handle', 'OTHER')]:
            s = sample(); s['endpoint_A']['geometry_connection'][field] = value
            self.assertEqual(self.run_sample(s)['candidate_role'], 'unknown')

    def test_scope(self):
        for scope in [{}, {'project': 'other', 'validation_area': 'compartment 1'}]:
            s = sample(); s['scope'] = scope
            self.assertEqual(self.run_sample(s)['candidate_role'], 'unknown')

    def test_preservation(self):
        s = sample(); s['project_specific_status'] = 'partial'; before = copy.deepcopy(s)
        r = self.run_sample(s)
        self.assertEqual(s, before)
        self.assertEqual(r['project_specific_status'], 'not_evaluated')
        self.assertFalse(r['design_net_quantity_eligible'])
        self.assertEqual(r['supporting_context'], s['edge_metadata'])
        self.assertEqual(r['prior_project_specific_status'], 'partial')

    def test_ambiguity_and_same_role(self):
        rules = copy.deepcopy(self.rules); other = copy.deepcopy(rules['rules'][0]); other['rule_id'] = 'Other'
        other['candidate_role'] = 'another_candidate'; rules['rules'].append(other)
        r = resolve_candidate(sample(), rules)
        self.assertEqual(r['candidate_status'], 'ambiguous')
        self.assertEqual(len(r['competing_candidate_roles']), 2)
        self.assertEqual(r['candidate_role'], 'unknown')
        other['candidate_role'] = rules['rules'][0]['candidate_role']
        r = resolve_candidate(sample(), rules)
        self.assertEqual(len(r['matched_rules']), 2)
        self.assertEqual(r['candidate_role'], 'alarm_or_linkage_bus')

    def test_directional(self):
        rules = copy.deepcopy(self.rules); rules['rules'][2]['directional'] = True
        self.assertEqual(resolve_candidate(sample('module_box', 'input_output_module'), rules)['candidate_role'], 'unknown')

    def test_verified_confidence(self):
        rules = copy.deepcopy(self.rules); rules['rules'][0]['validation_status'] = 'supported'
        self.assertEqual(resolve_candidate(sample(), rules)['candidate_confidence'], 'high')
        s = sample(); s['endpoint_A']['device_role']['role_status'] = 'inherited'
        self.assertEqual(resolve_candidate(s, rules)['candidate_confidence'], 'medium')

    def test_unknown_validation(self):
        rules = copy.deepcopy(self.rules); rules['rules'][0]['validation_status'] = 'new_unreviewed_status'
        self.assertEqual(resolve_candidate(sample(), rules)['candidate_role'], 'unknown')

    def test_loader_rejects_changed_source_and_invalid_binding(self):
        config = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
        config['source_rule_set'] = str((CONFIG.parent / config['source_rule_set']).resolve())
        variants = []
        changed = copy.deepcopy(config); changed['source_sha256'] = '0' * 64; variants.append(changed)
        missing = copy.deepcopy(config); del missing['bindings']['Rule B']; variants.append(missing)
        override = copy.deepcopy(config); override['bindings']['Rule A']['candidate_role'] = 'forced'; variants.append(override)
        no_scope = copy.deepcopy(config); no_scope['scope_keys'] = []; variants.append(no_scope)
        for variant in variants:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'rules.json'; path.write_text(json.dumps(variant), encoding='utf-8')
                with self.assertRaises(ValueError): load_rules(path)

    def test_rule_set_not_mutated_and_no_cad_input_used(self):
        original = copy.deepcopy(self.rules)
        s = sample(); s['raw_cad'] = {'fake_role': 'fire_damper', 'point_distance': 0}
        self.assertEqual(self.run_sample(s)['candidate_role'], 'alarm_or_linkage_bus')
        self.assertEqual(original, self.rules)

class RealFixtures(unittest.TestCase):
    def test_project_fixtures(self):
        fixtures = json.loads((ROOT / 'candidate-semantic/tests/fixtures/project-inputs.json').read_text(encoding='utf-8'))
        rules = load_rules(CONFIG)
        for fixture in fixtures:
            with self.subTest(edge=fixture['input']['edge_handle']):
                # Explicit legacy-input adapter: verify snapshot hashes and top-level
                # entities before supplying missing identity, without rewriting fixtures.
                import hashlib,re
                item=copy.deepcopy(fixture['input']);drawing=None
                project=item['scope']['project']
                for key in ('endpoint_A','endpoint_B'):
                    endpoint_item=item[key]
                    for kind,handle in [('geometry_connection',item['edge_handle']),('device_role',endpoint_item['device_role']['device_handle'])]:
                        record=endpoint_item[kind];matched=[]
                        synthetic_geometry=record.get('fixture_kind')=='synthetic'
                        sources=endpoint_item['device_role']['provenance'] if synthetic_geometry else record['provenance']
                        for source in sources:
                            path=Path(source['path'])
                            if path.name!='MEP-full-entity-report.txt':continue
                            data=path.read_bytes()
                            self.assertEqual(hashlib.sha256(data).hexdigest(),source['sha256'])
                            text=data.decode('utf-8-sig')
                            if not synthetic_geometry:
                                self.assertIsNotNone(re.search(r'(?m)^EntityHandle="?'+re.escape(handle)+r'"?\r?$',text),'Handle missing from verified snapshot: '+handle)
                            if kind=='geometry_connection':
                                self.assertIsNotNone(re.search(r'(?m)^EntityHandle="?'+re.escape(record['target_handle'])+r'"?\r?$',text),'Target missing from verified snapshot')
                            matched.append(re.search(r'(?m)^DWG=(.*?)\r?$',text)[1].strip().strip('"'))
                        self.assertTrue(matched)
                        self.assertEqual(len(set(matched)),1)
                        if drawing is not None:self.assertEqual(drawing,matched[0])
                        drawing=matched[0]
                        record['evidence_identity']={'project_id':project,'drawing_ref':drawing}
                        record['evidence_identity'].update({'edge_parent_path':[],'target_parent_path':[]} if kind=='geometry_connection' else {'parent_path':[]})
                item['evidence_identity']={'project_id':project,'drawing_ref':drawing,'parent_path':[]}
                result = resolve_candidate(item, rules)
                for key, value in fixture['expected'].items(): self.assertEqual(result[key], value)

if __name__ == '__main__': unittest.main(verbosity=2)
