"""Shared identity checks for eligibility and execution, without domain inference."""
PLACEHOLDER_ROLES = {'unknown', 'unresolved', 'partial', 'conflicting', 'rejected', 'not_evaluated'}


def canonical_id(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError('Nonempty canonical string identity required')
    return value


def approved_role(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip() and value.casefold() not in PLACEHOLDER_ROLES


def scope_identity(binding):
    if not isinstance(binding, dict):
        raise ValueError('Structured scope binding required')
    project, drawing, edge = (canonical_id(binding.get(k)) for k in ('project_id', 'drawing_ref', 'edge_handle'))
    segment = binding.get('segment_id')
    if segment is not None: canonical_id(segment)
    kind = binding.get('scope_type', 'segment' if segment is not None else 'edge')
    if kind not in ('edge', 'segment') or (kind == 'segment') != (segment is not None):
        raise ValueError('Scope kind/segment mismatch')
    path = binding.get('parent_path', [])
    if not isinstance(path, list): raise ValueError('Parent path must be an array')
    return project, drawing, kind, edge, segment, tuple(canonical_id(p) for p in path)


def physical_adjustment_identity(entry):
    # Classification and adjustment_id deliberately cannot create another physical leg.
    return (scope_identity(entry.get('owner')), canonical_id(entry.get('device')),
            canonical_id(entry.get('transition_type')))


def validate_plan_bindings(plan):
    identity = scope_identity(plan['binding'])
    if not approved_role(plan.get('approved_semantic_role')):
        raise ValueError('Explicit approved semantic role required')
    records = [plan['base_path'], plan['multiplier'], plan['specification'], plan['deduplication']] + plan['owned_adjustments']
    for record in records:
        if not record.get('provenance'): raise ValueError('Missing record provenance')
        if scope_identity(record.get('binding')) != identity: raise ValueError('Component scope binding mismatch')
    def audit_bindings(value):
        if isinstance(value, dict):
            if 'binding' in value and scope_identity(value['binding']) != identity:
                raise ValueError('Audit/execution scope binding mismatch')
            for child in value.values(): audit_bindings(child)
        elif isinstance(value, list):
            for child in value: audit_bindings(child)
    for field in ('geometry_basis', 'height_evidence', 'unit_execution_contract'):
        audit_bindings(plan.get(field))
    keys = set(); adjustment_ids = set()
    for entry in plan['owned_adjustments']:
        adjustment_id=canonical_id(entry.get('adjustment_id'))
        if adjustment_id in adjustment_ids: raise ValueError('Duplicate adjustment ID')
        adjustment_ids.add(adjustment_id)
        if scope_identity(entry.get('owner')) != identity: raise ValueError('Foreign adjustment owner')
        physical = physical_adjustment_identity(entry)
        if physical in keys: raise ValueError('Duplicate physical adjustment')
        keys.add(physical)
    aids = set()
    for assumption in plan['assumptions']:
        aid = canonical_id(assumption.get('id'))
        if aid in aids: raise ValueError('Duplicate assumption identity')
        aids.add(aid)
        if assumption.get('status') != 'approved' or not assumption.get('provenance'):
            raise ValueError('Unapproved or unsourced assumption')
        if scope_identity(assumption.get('scope', {}).get('binding')) != identity:
            raise ValueError('Assumption scope mismatch')
    for record in records:
        refs = record.get('assumption_refs', [])
        if record.get('assumptions_required') is True and not refs:
            raise ValueError('Required assumptions missing')
        if not isinstance(refs, list) or any(r not in aids for r in refs):
            raise ValueError('Unresolved assumption reference')
