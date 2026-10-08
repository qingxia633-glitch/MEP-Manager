"""Shared identity checks for eligibility and execution, without domain inference."""
PLACEHOLDER_ROLES = {'unknown', 'unresolved', 'partial', 'conflicting', 'rejected', 'not_evaluated'}


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_identity import canonical_id, scope_identity


def approved_role(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip() and value.casefold() not in PLACEHOLDER_ROLES


def physical_adjustment_identity(entry):
    # Classification and adjustment_id deliberately cannot create another physical leg.
    return (scope_identity(entry.get('owner')), canonical_id(entry.get('device')),
            canonical_id(entry.get('transition_type')))


def validate_plan_bindings(plan):
    identity = scope_identity(plan['binding'])
    validate_measurement_evidence(plan)
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


MEASUREMENT_EVIDENCE_CONTRACT_VERSION = 'measurement-evidence/2'


def validate_measurement_evidence(plan):
    identity = scope_identity(plan.get('binding'))
    mode = plan.get('base_path', {}).get('mode')
    if mode not in ('converted_2d', 'approved_3d'):
        raise ValueError('Unknown measurement mode')
    # All physical adjustments require height evidence; no inferred planar exemption.
    height_required = mode == 'approved_3d' or bool(plan.get('owned_adjustments'))
    requirement = plan.get('height_requirement')
    if requirement not in (None, 'required', 'not_applicable'):
        raise ValueError('Unknown height requirement')
    if height_required and requirement == 'not_applicable':
        raise ValueError('Height exemption conflicts with measurement mode/adjustments')
    for field in ('geometry_basis', 'height_evidence'):
        record = plan.get(field)
        if not isinstance(record, dict) or not record.get('provenance'):
            raise ValueError(field + ': missing required evidence/provenance')
        if scope_identity(record.get('binding')) != identity:
            raise ValueError(field + ': identity mismatch')
        if field == 'height_evidence' and not height_required and record.get('status') == 'not_applicable':
            if requirement != 'not_applicable' or not record.get('reason'):
                raise ValueError('Height exemption requires explicit requirement and reason')
            rule = record.get('measurement_rule')
            if (not isinstance(rule, dict) or not rule.get('rule_id') or
                rule.get('status') not in ('supported', 'approved') or not rule.get('provenance') or
                rule.get('measurement_mode') != mode or rule.get('height_requirement') != 'not_applicable'):
                raise ValueError('Height exemption requires a reviewed measurement rule')
            if scope_identity(rule.get('binding')) != identity:
                raise ValueError('Height exemption rule identity mismatch')
        elif record.get('status') != 'supported':
            raise ValueError(field + ': required evidence not supported')
