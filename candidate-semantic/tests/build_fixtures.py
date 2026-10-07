"""Offline fixture preparation only: invoke upstream resolvers, never classify raw CAD."""
import importlib.util
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result

def main():
    geometry = module('geometry_upstream', 'geometry-connection/resolver.py')
    roles = module('roles_upstream', 'device-role/resolver.py')
    snapshot = ROOT / 'local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'
    probes = [ROOT / 'local_test_data' / p / 'block-definition-probe.txt' for p in [
        'module-13304-probe-20261005', 'fire-alarm-smoke-block-Equip00002649-probe-20260926',
        'block-definition-probe.txt', 'module-13017-child-10B16-probe-20261005', 'valve-132F7-probe-20261005']]
    gc = geometry.DrawingContext.from_reports(snapshot, probes)
    rc = roles.RoleContext.from_reports(snapshot, probes)
    scope = {'project': 'current garage fire-alarm project', 'validation_area': 'compartment 1'}
    history_path = ROOT / 'outputs/fire-alarm-semantic-pattern-validation-20261005/evidence.json'
    history = json.loads(history_path.read_text(encoding='utf-8-sig'))
    semantics_path = ROOT / 'outputs/module-four-edge-electrical-semantics-20261005/evidence.json'
    semantics = json.loads(semantics_path.read_text(encoding='utf-8-sig'))
    prior = {e['edge_id']: e['final_semantic_status'] for e in semantics['edges']}
    prior.update({s['edge_handle']: s.get('project_specific_status') for s in history['samples']})
    pairs = [('13CF0', '12D5A', '13304'), ('13CE8', '134D9', '12D65'),
             ('13CE9', '134D9', '13304'), ('14147', '134D9', '13017'), ('14423', '132FB', '132F7')]
    for s in history['samples']:
        if s['edge_handle'] in ('13CD5', '13D0F', '13CFD', '13D15'):
            pairs.append((s['edge_handle'], s['endpoint_A_role'][0]['device'], s['endpoint_B_role'][0]['device']))
    fixtures = []
    for edge, a, b in pairs:
        item = {'edge_handle': edge, 'scope': scope.copy(), 'project_specific_status': prior.get(edge),
                'edge_metadata': {'layer': gc.entities[edge].get('layer'), 'specification_evidence': [], 'nearby_text': []},
                'provenance': [{'source': 'upstream resolver outputs from current project reports'},
                               {'path': str(semantics_path), 'sha256': hashlib.sha256(semantics_path.read_bytes()).hexdigest(), 'use': 'unchanged prior semantic status'},
                               {'path': str(history_path), 'sha256': hashlib.sha256(history_path.read_bytes()).hexdigest(),
                                'use': 'independent sample endpoint identity/order only'}],
                'fixture_kind': 'real_project'}
        for key, target, index in [('endpoint_A', a, 0), ('endpoint_B', b, -1)]:
            item[key] = {'geometry_connection': geometry.resolve_connection(edge, gc.entities[edge]['vertices'][index], target, gc, .001),
                         'device_role': roles.resolve_device_role(target, rc)}
        print(edge, [(item[k]['geometry_connection']['geometric_connection_status'],
                      item[k]['device_role']['canonical_role'], item[k]['device_role']['role_status']) for k in ('endpoint_A','endpoint_B')])
        expected_role = ('unknown' if edge == '14423' else 'bus_or_module_box_feed' if edge in ('14147','13CFD') else 'alarm_or_linkage_bus')
        expected_grade = 'unknown' if edge == '14423' else 'low' if edge in ('13D0F','13D15') else 'medium'
        fixtures.append({'input': item, 'expected': {'candidate_role': expected_role, 'candidate_confidence': expected_grade,
                                                   'candidate_status': 'unresolved' if edge == '14423' else 'candidate',
                                                   'project_specific_status': 'not_evaluated', 'design_net_quantity_eligible': False}})
    # Real inherited role, synthetic endpoint relation: never label this as project wiring.
    hybrid = {'edge_handle': 'SYNTHETIC-INHERITED', 'scope': scope.copy(), 'fixture_kind': 'synthetic_geometry_real_role',
              'provenance': [{'source': '12EA0 real role + explicitly synthetic geometry relation'}]}
    for key, target in [('endpoint_A','12EA0'),('endpoint_B','13304')]:
        hybrid[key] = {'geometry_connection': {'edge_handle': 'SYNTHETIC-INHERITED', 'target_handle': target,
                                               'geometric_connection_status': 'supported', 'fixture_kind': 'synthetic'},
                       'device_role': roles.resolve_device_role(target, rc)}
    fixtures.append({'input': hybrid, 'expected': {'candidate_role': 'alarm_or_linkage_bus', 'candidate_confidence': 'low'}})
    folder = ROOT / 'candidate-semantic/tests/fixtures'; folder.mkdir(exist_ok=True)
    (folder / 'project-inputs.json').write_text(json.dumps(fixtures, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__': main()
