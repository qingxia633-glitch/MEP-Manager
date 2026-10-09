"""Load immutable project rules plus an explicit machine-readable project binding."""
import hashlib
import json
from pathlib import Path


def load_rules(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(config.get('scope_keys'), list) or not config['scope_keys'] or any(not isinstance(k, str) or not k for k in config['scope_keys']):
        raise ValueError('Explicit project scope keys required')
    source = (path.parent / config['source_rule_set']).resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != config['source_sha256'].lower():
        raise ValueError('Source rule hash mismatch; review project binding before reuse')
    raw = json.loads(source.read_text(encoding='utf-8-sig'))
    rules = raw['rules']
    ids = [r['rule_id'] for r in rules]
    if len(set(ids)) != len(ids) or set(ids) != set(config['bindings']):
        raise ValueError('Project bindings must cover each source rule exactly once')
    for rule in rules:
        if rule.get('may_generate_design_net_quantity') is not False:
            raise ValueError('Only candidate-only rules are admitted')
        binding = config['bindings'][rule['rule_id']]
        kind = binding.get('kind')
        if kind not in ('role_pair', 'context_restriction'):
            raise ValueError('Unsupported rule kind')
        if kind == 'role_pair':
            if not rule.get('candidate_role') or rule['candidate_role'] in ('unknown', 'unresolved'):
                raise ValueError('Classification rule must declare a candidate role')
            for key in ('roles_A', 'roles_B'):
                if not isinstance(binding.get(key), list) or not binding[key] or any(not isinstance(v, str) or not v or v == 'unknown' for v in binding[key]):
                    raise ValueError('Explicit nonempty endpoint role sets required')
            if not isinstance(binding.get('directional', False), bool):
                raise ValueError('directional must be boolean')
        if set(binding) - {'kind', 'roles_A', 'roles_B', 'directional', 'forbidden_as_sole_evidence'}:
            raise ValueError('Binding cannot override source rule semantics')
        rule.update(binding)
    policy = config['confidence_policy']
    if any(v not in ('high', 'medium', 'low', 'unknown') for v in policy.values()):
        raise ValueError('Confidence must be an ordinal evidence grade')
    return {'rules': rules, 'confidence_policy': policy, 'scope_keys': config['scope_keys'],
            'provenance': [{'path': str(source), 'sha256': digest},
                           {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}],
            'assumptions': config.get('assumptions', [])}
