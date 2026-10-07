"""Evaluate supplied project witnesses; never infer missing facts or approvals."""
from copy import deepcopy
from model import CHANNELS, STRENGTHS, combine


def _same_context(record, context):
    return all(context.get(k) and record.get(k) == context[k] for k in ('project_id', 'drawing_ref'))


def _bound(record, target, context):
    return (record.get('target_id') == target.get('id') and
            record.get('target_kind') == target.get('kind') and _same_context(record, context))


def _trusted(record):
    return bool(record.get('provenance')) and record.get('evidence_strength') in STRENGTHS


def _condition(condition, request):
    channel = condition.get('channel')
    result = dict(condition_id=condition['condition_id'], expected=condition.get('expected'),
                  actual=[], status='unknown', evidence=[], ignored_evidence=[])
    if channel not in CHANNELS:
        result['reason'] = 'unsupported witness channel'
        return result
    records = [r for r in request.get(channel, []) + request.get('conflicting_evidence', [])
               if r.get('key') == condition.get('key')]
    for r in records:
        if _bound(r, request['target_object'], request['context']) and _trusted(r):
            result['evidence'].append(deepcopy(r))
        else:
            result['ignored_evidence'].append(deepcopy(r))
    usable = result['evidence']
    values = [r['value'] for r in usable if r.get('status') == 'supported' and 'value' in r]
    result['actual'] = deepcopy(values)
    if any(r.get('status') == 'conflicting' for r in usable) or any(type(v) is not type(values[0]) or v != values[0] for v in values[1:]):
        result['status'] = 'conflicting'
    elif any(r.get('status') != 'supported' or r.get('value') is None for r in usable):
        result['status'] = 'unknown'
    elif values:
        # Keep bool and numeric facts distinct (True must not equal 1).
        result['status'] = 'true' if type(values[0]) is type(condition.get('expected')) and values[0] == condition['expected'] else 'false'
    return result


def _propagation(rule, request):
    key = rule['propagation_key']
    fields = ('source_annotation', 'root_target', 'propagation_relation',
              'bounded_set', 'propagation_boundary', 'termination_condition')
    records = [r for r in request.get('propagation_sources', [])
               if r.get('key') == key and _same_context(r, request['context']) and _trusted(r)]
    result = dict(condition_id='bounded_propagation', expected='target in proven bounded set',
                  actual=[], evidence=deepcopy(records), status='unknown')
    if not records:
        return result
    if any(r.get('status') == 'conflicting' for r in records):
        result['status'] = 'conflicting'
        return result
    if any(r.get('status') != 'supported' or any(not r.get(f) for f in fields if f != 'bounded_set') or
           not isinstance(r.get('bounded_set'), list) or
           not isinstance(r.get('root_target'), dict) or
           not r['root_target'].get('id') or r['root_target'].get('kind') not in ('edge','device','group') or
           any(not isinstance(t,dict) or not t.get('id') or t.get('kind') not in ('edge','device','group')
               for t in r['bounded_set']) for r in records):
        return result
    descriptions = [{f: r[f] for f in fields} for r in records]
    if any(d != descriptions[0] for d in descriptions[1:]):
        result['status'] = 'conflicting'
        return result
    target = request['target_object']
    result['actual'] = descriptions
    result['status'] = 'true' if {'id': target['id'], 'kind': target['kind']} in records[0]['bounded_set'] else 'false'
    return result


def resolve(rule, request):
    """Return an unapproved RuleBindingProposal. Evidence remains caller-supplied."""
    if not rule.get('rule_id') or not rule.get('rule_version') or not rule.get('provenance'):
        raise ValueError('versioned rule identity and provenance required')
    if rule.get('binding_scope') not in ('object','region','drawing','fire_compartment','system','local_group'):
        raise ValueError('recognized binding scope required')
    target = request['target_object']
    if not target.get('id') or target.get('kind') not in ('edge', 'device', 'group'):
        raise ValueError('typed target required')
    conditions = deepcopy(rule.get('conditions', []))
    conditions += deepcopy(rule.get('scope_conditions', []))
    ids = [c.get('condition_id') for c in conditions + rule.get('exclusions', [])]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError('unique condition ids required')
    for c in conditions + rule.get('exclusions', []):
        if not c.get('key') or 'expected' not in c or c['expected'] is None:
            raise ValueError('condition key and non-null expected value required')
    evaluated = [_condition(c, request) for c in conditions]
    scope_channel = {'region':'region_memberships','fire_compartment':'region_memberships',
                     'drawing':'region_memberships','system':'system_memberships',
                     'local_group':'local_group_memberships'}.get(rule.get('binding_scope'))
    if scope_channel and not any(c.get('channel') == scope_channel for c in rule.get('scope_conditions', [])):
        evaluated.append(dict(condition_id='required_scope_membership', expected=scope_channel,
                              actual=None, status='unknown', evidence=[]))
    if not conditions:
        evaluated.append(dict(condition_id='required_conditions', expected='nonempty', actual=[], status='unknown', evidence=[]))
    if rule.get('target_ids') is not None:
        evaluated.append(dict(condition_id='object_scope', expected=rule['target_ids'], actual=target['id'],
                              status='true' if target['id'] in rule['target_ids'] else 'false', evidence=deepcopy(rule['provenance'])))
    if rule.get('propagation_key'):
        evaluated.append(_propagation(rule, request))
    exclusions = [_condition(c, request) for c in rule.get('exclusions', [])]
    # Exclusions are positive predicates: true means excluded, unknown remains unknown.
    states = [c['status'] for c in evaluated] + [
        {'true': 'false', 'false': 'true'}.get(c['status'], c['status']) for c in exclusions]
    status = combine(states)
    context_ok = all(request.get('context', {}).get(k) and rule.get('context', {}).get(k) == request['context'][k]
                     for k in ('project_id', 'drawing_ref'))
    if not context_ok:
        evaluated.append(dict(condition_id='rule_context', expected=rule.get('context'),
                              actual=request.get('context'), status='unknown', evidence=[]))
        status = combine(states + ['unknown'])
    all_checks = evaluated + exclusions
    return dict(object_type='RuleBindingProposal', resolver_version='0.1',
                target_id=target['id'], target_kind=target['kind'], context=deepcopy(request['context']),
                rule_id=rule['rule_id'], rule_version=rule['rule_version'], applicability_status=status,
                evaluated_conditions=evaluated, matched_scope=deepcopy(rule.get('binding_scope')) if status == 'applicable' else None,
                membership_evidence=[deepcopy(r) for ch in ('region_memberships','system_memberships','local_group_memberships')
                                     for r in request.get(ch, []) if _bound(r, target, request['context'])],
                exclusions_checked=exclusions,
                unresolved_conditions=[c['condition_id'] for c in all_checks if c['status'] == 'unknown'],
                conflicting_conditions=[c['condition_id'] for c in all_checks if c['status'] == 'conflicting'],
                semantic_effect=deepcopy(rule.get('semantic_effect')), specification_effect=deepcopy(rule.get('specification_effect')),
                installation_effect=deepcopy(rule.get('installation_effect')), binding_strength=rule.get('binding_strength'),
                propagation_status=next((c['status'] for c in evaluated if c['condition_id']=='bounded_propagation'), 'not_requested'),
                provenance={'rule':deepcopy(rule['provenance']), 'request':deepcopy(request.get('provenance', []))},
                assumptions=['Witnesses must be independently established; no inference from confidence, proximity or specification',
                             'False required condition takes precedence; all conflicting checks are retained',
                             'Applicability is not project semantic approval'],
                may_submit_to_project_gate=status == 'applicable')


def to_gate_evidence(proposal):
    """Create a pending-review Gate bundle, never a self-approved authorization."""
    role = proposal.get('semantic_effect', {})
    if (proposal.get('applicability_status') != 'applicable' or not proposal.get('may_submit_to_project_gate') or
            proposal.get('target_kind') != 'edge' or not isinstance(role, dict) or not role.get('semantic_role')):
        raise ValueError('applicable edge with explicit semantic effect required')
    context = proposal['context']; key = f"{proposal['rule_id']}:{proposal['rule_version']}:{proposal['target_id']}"
    return dict(**context, provenance=[deepcopy(proposal)], evidence=[dict(
        evidence_id=key, evidence_type='reviewed_project_rule', evidence_strength='project_rule_binding',
        status='unresolved', semantic_role=role['semantic_role'], assertion='affirm', binding_id=key,
        provenance=[deepcopy(proposal)])], bindings=[dict(
        **context, binding_id=key, edge_handle=proposal['target_id'], review_status='pending',
        evidence_ids=[key], provenance=[deepcopy(proposal)])])
