"""Pure reviewed-evidence contracts. No approvals, source acquisition or inference."""
import re
import importlib.util
from pathlib import Path
from evidence_identity import canonical_id, scope_identity

VERSIONS = {'authorization': 'EvidenceAuthorizationContract/1',
            'provenance': 'ProvenanceRecordContract/1',
            'assumptions': 'AssumptionDependencyPolicy/1'}
# Reuse the Gate vocabulary without evaluating candidate semantics or bindings.
_spec = importlib.util.spec_from_file_location('_admission_evidence_vocabulary',
    Path(__file__).resolve().parents[1] / 'project-evidence-gate/evidence.py')
_vocabulary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vocabulary)
DIRECT = _vocabulary.DIRECT_TYPES


def strings(value):
    if not isinstance(value, list) or not value:
        raise ValueError('Nonempty reference list required')
    result = [canonical_id(v) for v in value]
    if len(set(result)) != len(result):
        raise ValueError('Duplicate reference')
    return result


def authorization(plan):
    gate = plan['semantic_gate']; identity = scope_identity(plan['binding'])
    evidence = gate['accepted_evidence']; bindings = gate.get('binding_targets')
    if not isinstance(bindings, list) or not bindings:
        raise ValueError('EvidenceAuthorizationContract: reviewed bindings missing')
    by_id = {}
    for binding in bindings:
        if not isinstance(binding, dict): raise ValueError('Invalid authorization binding')
        bid = canonical_id(binding.get('binding_id'))
        if bid in by_id: raise ValueError('Duplicate authorization binding')
        by_id[bid] = binding
        if scope_identity(binding) != identity: raise ValueError('Foreign authorization binding')
        if binding.get('review_status') not in ('approved', 'supported', 'reviewed'):
            raise ValueError('Authorization binding not reviewed')
        if binding.get('semantic_role') != plan['approved_semantic_role'] or binding.get('assertion') != 'affirm':
            raise ValueError('Authorization binding role/assertion mismatch')
        strings(binding.get('evidence_ids'))
    assigned = {bid: set() for bid in by_id}; seen = set()
    for e in evidence:
        eid = canonical_id(e.get('evidence_id')); bid = canonical_id(e.get('binding_id'))
        if eid in seen: raise ValueError('Duplicate authorization evidence')
        seen.add(eid)
        if e.get('evidence_strength') not in DIRECT.get(e.get('evidence_type'), set()):
            raise ValueError('Non-authorizing evidence type/strength')
        if bid not in by_id or eid not in by_id[bid]['evidence_ids']:
            raise ValueError('Evidence/binding forward reference mismatch')
        if scope_identity(e.get('object_identity')) != identity:
            raise ValueError('Foreign authorization evidence')
        assigned[bid].add(eid)
    for bid, binding in by_id.items():
        if assigned[bid] != set(binding['evidence_ids']):
            raise ValueError('Evidence/binding reverse reference mismatch')


def leaf_assumptions(plan):
    def visit(value):
        if isinstance(value, dict):
            if 'assumptions_required' in value or value.get('assumption_refs'):
                raise ValueError('AssumptionDependencyPolicy: nested dependencies unsupported')
            if 'assumption_refs' in value and value['assumption_refs'] != []:
                raise ValueError('Invalid assumption dependency declaration')
            for v in value.values(): visit(v)
        elif isinstance(value, list):
            for v in value: visit(v)
    for assumption in plan['assumptions']: visit(assumption)


def provenance(plan):
    identity = scope_identity(plan['binding']); sources = plan['source_evidence_hashes']
    if plan['provenance'] != sources:
        raise ValueError('Provenance/source index mismatch')
    for sid, source in sources.items():
        canonical_id(sid)
        if not isinstance(source, dict) or source.get('source_id') != sid:
            raise ValueError('Source identity missing/mismatched')
        if not isinstance(source.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
            raise ValueError('Invalid source hash')
        if source.get('status') != 'verified' or scope_identity(source.get('object_identity')) != identity:
            raise ValueError('Source not verified for current object')
        strings(source.get('evidence_refs'))
    used = set()

    def check(record, path):
        if not isinstance(record, dict):
            raise ValueError(path + ': structured evidence record required')
        records = record.get('provenance')
        if not isinstance(records, list) or not records:
            raise ValueError(path + ': structured provenance required')
        for ref in records:
            if not isinstance(ref, dict): raise ValueError(path + ': invalid provenance record')
            sid = canonical_id(ref.get('source_id')); source = sources.get(sid)
            if (not source or ref.get('sha256') != source['sha256'] or ref.get('status') != 'verified' or
                ref.get('evidence_ref') != path or path not in source['evidence_refs'] or
                ref.get('binding_ref') != '/binding'):
                raise ValueError(path + ': source hash/status/evidence binding mismatch')
            if scope_identity(ref.get('object_identity')) != identity:
                raise ValueError(path + ': foreign provenance identity')
            pointer = ref.get('pointer')
            if not isinstance(pointer, str) or (pointer != '' and not pointer.startswith('/')):
                raise ValueError(path + ': source pointer required')
            used.add((sid, path))

    def walk(value, path):
        if isinstance(value, dict):
            if 'provenance' in value: check(value, path)
            for k, v in value.items():
                if k != 'provenance': walk(v, path + '/' + k.replace('~','~0').replace('/','~1'))
        elif isinstance(value, list):
            for i, v in enumerate(value): walk(v, path + '/' + str(i))

    # Required roots: deleting the provenance field cannot avoid validation.
    for field in ('base_path','multiplier','specification','deduplication','geometry_basis',
                  'height_evidence','reporting_policy'):
        check(plan[field], '/' + field)
        walk(plan[field], '/' + field)
    for field in ('owned_adjustments','assumptions'):
        for i, record in enumerate(plan[field]):
            check(record, '/' + field + '/' + str(i)); walk(record, '/' + field + '/' + str(i))
    gate = plan['semantic_gate']
    for group in ('accepted_evidence','binding_targets'):
        for i, record in enumerate(gate[group]):
            path='/semantic_gate/'+group+'/'+str(i);check(record,path);walk(record,path)
    check(plan['geometry_basis']['conversion'], '/geometry_basis/conversion')
    rule = plan['height_evidence'].get('measurement_rule')
    if rule is not None: check(rule, '/height_evidence/measurement_rule')
    conversion = plan['unit_conversion_contract']
    if conversion.get('kind') == 'cad_geometry_scale':
        # Identical audit copies retain the original source citation.
        check(conversion, '/geometry_basis/conversion/reviewed_scale_contract')
    execution = plan['unit_execution_contract']
    if len(execution['components']) != 1 + len(plan['owned_adjustments']):
        raise ValueError('Execution provenance component inventory mismatch')
    for i, term in enumerate(execution['components']):
        path='/unit_execution_contract/components/'+str(i)
        origin='/base_path' if i==0 else '/owned_adjustments/'+str(i-1)
        original=plan['base_path'] if i==0 else plan['owned_adjustments'][i-1]
        if term.get('provenance') == original.get('provenance'):path=origin
        check(term,path);walk(term,path)
    multiplier_path='/multiplier' if execution['multiplier'].get('provenance')==plan['multiplier'].get('provenance') else '/unit_execution_contract/multiplier'
    check(execution['multiplier'],multiplier_path)
    if plan.get('corrections_applied',{}).get('evidence'):
        walk(plan['corrections_applied']['evidence'],'/corrections_applied/evidence')
    for sid, source in sources.items():
        if any((sid, ref) not in used for ref in source['evidence_refs']):
            raise ValueError('Source index contains unbound evidence references')


def validate_evidence_contracts(plan):
    if plan.get('admission_contracts') != VERSIONS:
        raise ValueError('Evidence admission profile missing/unsupported; source-backed migration required')
    authorization(plan)
    leaf_assumptions(plan)
    provenance(plan)
