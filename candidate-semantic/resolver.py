"""Structured evidence -> candidate semantics. No CAD, geometry or role parsing."""
from copy import deepcopy

GRADES = ['unknown', 'low', 'medium', 'high']


def resolve_candidate(item, rule_set):
    result = {'model_type': 'CandidateSemanticEvidence', 'resolver_version': '0.1',
              'edge_handle': item.get('edge_handle'), 'candidate_role': 'unknown',
              'candidate_confidence': 'unknown', 'candidate_status': 'unresolved',
              'matched_rule_id': None, 'matched_rules': [], 'competing_candidate_roles': [],
              'rule_validation_status': None, 'supporting_evidence': [], 'limiting_evidence': [],
              'conflicting_evidence': [], 'project_specific_status': 'not_evaluated',
              'prior_project_specific_status': item.get('project_specific_status'),
              'design_net_quantity_eligible': False,
              'supporting_context': deepcopy(item.get('edge_metadata', {})),
              'layer_context': deepcopy(item.get('edge_metadata', {}).get('layer')),
              'specification_context': deepcopy(item.get('edge_metadata', {}).get('specification_evidence')),
              'provenance': {'input': deepcopy(item.get('provenance', [])),
                             'rule_set': deepcopy(rule_set.get('provenance', [])), 'endpoints': {}},
              'assumptions': deepcopy(rule_set.get('assumptions', [])) +
                            ['No electrical direction inferred from endpoint order',
                             'Candidate evidence never establishes project-specific identity or quantities']}
    blocked = False
    partial_geometry = False
    inherited = False
    for key in ('endpoint_A', 'endpoint_B'):
        endpoint = item.get(key, {})
        geo = endpoint.get('geometry_connection', {})
        role = endpoint.get('device_role', {})
        gs, rs = geo.get('geometric_connection_status'), role.get('role_status')
        result[key] = {'target_handle': geo.get('target_handle'), 'geometry_status': gs,
                       'canonical_role': role.get('canonical_role', 'unknown'), 'role_status': rs,
                       'role_evidence_status': rs}
        result['provenance']['endpoints'][key] = deepcopy(endpoint)
        if (not item.get('edge_handle') or geo.get('edge_handle') != item['edge_handle'] or
                not geo.get('target_handle') or geo['target_handle'] != role.get('device_handle')):
            result['limiting_evidence'].append({'endpoint': key, 'blocker': 'evidence_identity_mismatch'})
            blocked = True
        if gs != 'supported':
            result['limiting_evidence'].append({'endpoint': key, 'blocker': 'geometry_blocker', 'status': gs})
            if gs == 'partial': partial_geometry = True
            else: blocked = True
        if rs not in ('supported', 'inherited') or role.get('canonical_role', 'unknown') == 'unknown':
            result['limiting_evidence'].append({'endpoint': key, 'blocker': 'role_evidence_blocker', 'status': rs})
            if rs == 'conflicting': result['conflicting_evidence'].append(deepcopy(role))
            blocked = True
        if rs == 'inherited':
            inherited = True
            result['limiting_evidence'].append({'endpoint': key, 'role_evidence_status': 'inherited'})
    result['context_restrictions'] = [deepcopy(r) for r in rule_set['rules'] if r['kind'] == 'context_restriction']
    if blocked: return result
    a, b = result['endpoint_A']['canonical_role'], result['endpoint_B']['canonical_role']
    matches = []
    for rule in rule_set['rules']:
        if rule['kind'] != 'role_pair': continue
        direct = a in rule['roles_A'] and b in rule['roles_B']
        reverse = not rule.get('directional', False) and b in rule['roles_A'] and a in rule['roles_B']
        if not (direct or reverse): continue
        if any(not rule.get('scope', {}).get(k) or item.get('scope', {}).get(k) != rule['scope'][k]
               for k in rule_set['scope_keys']):
            result['limiting_evidence'].append({'rule_id': rule['rule_id'], 'blocker': 'project_scope_mismatch_or_missing'})
            continue
        grade = rule_set['confidence_policy'].get(rule['validation_status'], 'unknown')
        if grade == 'unknown':
            result['limiting_evidence'].append({'rule_id': rule['rule_id'], 'blocker': 'rule_validation_not_admitted',
                                               'status': rule['validation_status']})
            continue
        matches.append((rule, grade))
    if not matches:
        result['limiting_evidence'].append({'blocker': 'no_admitted_role_pair_rule'})
        return result
    result['matched_rules'] = [deepcopy(r) for r, _ in matches]
    ids = [r['rule_id'] for r, _ in matches]
    result['matched_rule_id'] = ids[0] if len(ids) == 1 else ids
    statuses = list(dict.fromkeys(r['validation_status'] for r, _ in matches))
    result['rule_validation_status'] = statuses[0] if len(statuses) == 1 else statuses
    roles = sorted(set(r['candidate_role'] for r, _ in matches))
    for rule, grade in matches:
        result['supporting_evidence'].append({'rule_id': rule['rule_id'], 'endpoint_roles': [a, b],
                                              'validation_status': rule['validation_status']})
        result['limiting_evidence'].extend(deepcopy(rule.get('conflicting_or_missing_evidence', [])))
    if len(roles) > 1:
        result['candidate_status'] = 'ambiguous'
        result['competing_candidate_roles'] = roles
        result['conflicting_evidence'].append({'competing_rules': ids, 'roles': roles})
        return result
    result['candidate_role'] = roles[0]
    grade = min(GRADES.index(g) for _, g in matches)
    if inherited: grade = max(1, grade - 1)
    result['candidate_confidence'] = 'unknown' if partial_geometry else GRADES[grade]
    result['candidate_status'] = 'partial' if partial_geometry else 'candidate'
    return result
