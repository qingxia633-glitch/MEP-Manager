"""Untrusted-plan admission. Pure verification; no CAD or engineering inference."""
from decimal import Decimal, Context, localcontext, Inexact, Rounded
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.builder-deps'))
from jsonschema import Draft202012Validator
from quantity_contract import scope_identity, validate_plan_bindings
from unit_contract import conversion_contract
from evidence_contracts import validate_evidence_contracts

SCHEMA = json.loads((Path(__file__).parent / 'schemas/quantity-build-plan-v03.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA)
ADMISSION_EVIDENCE_REGISTRY = (
    'base_path', 'multiplier', 'specification', 'deduplication', 'owned_adjustments',
    'geometry_basis', 'height_evidence', 'semantic_gate', 'approved_semantic_binding',
    'unit_conversion_contract', 'unit_execution_contract', 'reporting_policy', 'corrections_applied',
    'provenance', 'source_evidence_hashes', 'formula_components', 'arithmetic_policy',
)


def exact_number(value):
    if isinstance(value, (bool, float)) or not isinstance(value, (str, int)):
        raise ValueError('Exact decimal string/integer required in raw conversion')
    number = Decimal(value)
    if not number.is_finite() or number < 0:
        raise ValueError('Finite nonnegative raw conversion value required')
    return number


def validate_gate(plan):
    gate = plan['semantic_gate']; identity = scope_identity(plan['binding'])
    if (gate.get('project_specific_status') != 'supported' or
        gate.get('semantic_gate_passed') is not True or
        gate.get('design_net_quantity_eligible') is not True or
        gate.get('approved_semantic_role') != plan['approved_semantic_role']):
        raise ValueError('Semantic Gate approval/role contract failed')
    for record in (gate.get('object_identity'), gate.get('provenance', {}).get('context')):
        if scope_identity(record) != identity:
            raise ValueError('Semantic Gate identity/context mismatch')
    if gate.get('edge_handle') != plan['binding']['edge_handle'] or gate.get('segment_id') != plan['binding'].get('segment_id'):
        raise ValueError('Semantic Gate edge/segment mismatch')
    accepted = gate.get('accepted_evidence')
    if not isinstance(accepted, list) or not accepted:
        raise ValueError('Semantic Gate accepted evidence missing')
    for evidence in accepted:
        if not isinstance(evidence, dict) or not evidence.get('provenance'):
            raise ValueError('Accepted evidence provenance missing')
        if scope_identity(evidence.get('object_identity')) != identity:
            raise ValueError('Accepted evidence foreign identity')
        if evidence.get('status') != 'supported' or evidence.get('semantic_role') != plan['approved_semantic_role'] or evidence.get('assertion') != 'affirm':
            raise ValueError('Accepted evidence not approved for this role')
    if gate.get('conflicting_evidence') or gate.get('limiting_evidence'):
        raise ValueError('Semantic Gate retains conflicting/limiting evidence')
    for record in gate.get('binding_targets', []):
        if scope_identity(record) != identity:
            raise ValueError('Gate binding target identity mismatch')
    if 'approved_semantic_binding' in plan:
        if scope_identity(plan['approved_semantic_binding']) != identity:
            raise ValueError('Approved semantic binding mismatch')


def validate_geometry_conversion(plan):
    geometry = plan['geometry_basis']; conversion = geometry.get('conversion')
    if not isinstance(conversion, dict) or conversion.get('status') != 'supported' or not conversion.get('provenance'):
        raise ValueError('Raw geometry conversion missing/unapproved')
    identity = scope_identity(plan['binding'])
    if scope_identity(conversion.get('binding')) != identity or geometry.get('source_entity') != plan['binding']['edge_handle']:
        raise ValueError('Raw geometry conversion/source identity mismatch')
    if conversion.get('from_unit') != geometry.get('source_unit') or conversion.get('to_unit') != geometry.get('engineering_unit'):
        raise ValueError('Raw conversion source/target mismatch')
    raw = exact_number(geometry.get('base_length'))
    factor = exact_number(conversion.get('factor')); converted = exact_number(conversion.get('converted_length'))
    if raw <= 0 or factor <= 0:
        raise ValueError('Positive raw geometry and factor required')
    verified_contract = conversion_contract(conversion, plan['binding'])
    if exact_number(verified_contract.get('factor')) != factor:
        raise ValueError('Reviewed contract factor must be the same exact decimal')
    if plan['unit_conversion_contract'] != verified_contract:
        raise ValueError('Versioned conversion contract differs from raw geometry contract')
    precision = max(28, len(raw.as_tuple().digits) + len(factor.as_tuple().digits))
    with localcontext(Context(prec=precision)) as context:
        context.traps[Inexact] = True; context.traps[Rounded] = True
        if raw * factor != converted:
            raise ValueError('Raw geometry conversion result is not exact')
    base = plan['base_path']
    if exact_number(base['value']) <= 0:
        raise ValueError('Positive reviewed base path required')
    if geometry['engineering_unit'] != base['unit']:
        raise ValueError('Engineering unit/base path unit mismatch')
    if base['mode'] == 'converted_2d' and exact_number(base['value']) != converted:
        raise ValueError('Converted geometry/base path mismatch')
    if plan['unit_execution_contract'].get('raw_geometry_conversion') != conversion:
        raise ValueError('Execution raw conversion does not match geometry basis')


def validate_assumption_registry(plan):
    assumptions = {a['id']: a for a in plan['assumptions']}
    identity = scope_identity(plan['binding'])

    def visit(record, path):
        if isinstance(record, list):
            for i, child in enumerate(record): visit(child, path + '/' + str(i))
        elif isinstance(record, dict):
            refs = record.get('assumption_refs', [])
            if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
                raise ValueError(path + ': invalid assumption refs')
            if 'assumptions_required' in record and type(record['assumptions_required']) is not bool:
                raise ValueError(path + ': invalid assumptions_required')
            if record.get('assumptions_required') is True and not refs:
                raise ValueError(path + ': required assumptions missing')
            for ref in refs:
                assumption = assumptions.get(ref)
                if not assumption or assumption.get('status') != 'approved' or not assumption.get('provenance'):
                    raise ValueError(path + ': unresolved/unapproved assumption')
                scope = assumption.get('scope', {})
                if scope_identity(scope.get('binding')) != identity:
                    raise ValueError(path + ': assumption identity mismatch')
                expected = scope.get('conditions'); actual = record.get('conditions')
                if not isinstance(expected, dict) or not expected or not isinstance(actual, dict):
                    raise ValueError(path + ': assumption applicability conditions missing')
                if any(key not in actual or
                       json.dumps(actual[key], sort_keys=True, allow_nan=False) !=
                       json.dumps(value, sort_keys=True, allow_nan=False)
                       for key, value in expected.items()):
                    raise ValueError(path + ': assumption conditions unsatisfied')
            for key, child in record.items(): visit(child, path + '/' + key)

    for field in ADMISSION_EVIDENCE_REGISTRY:
        visit(plan.get(field), field)


def validate_executable_plan_contract(plan):
    errors = sorted(VALIDATOR.iter_errors(plan), key=lambda e: str(list(e.absolute_path)))
    if errors:
        raise ValueError('v0.3 schema: ' + '; '.join('/' + '/'.join(map(str, e.absolute_path)) + ': ' + e.message for e in errors))
    validate_plan_bindings(plan)
    validate_gate(plan)
    validate_evidence_contracts(plan)
    validate_geometry_conversion(plan)
    validate_assumption_registry(plan)
