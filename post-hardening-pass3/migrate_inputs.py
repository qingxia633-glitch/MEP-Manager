"""Additive local v0.3 fixtures; each delta points to existing reviewed sources."""
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/post-hardening-pass3-20261008'
sys.path.insert(0, str(ROOT / 'quantity-eligibility'))
from plan_v02 import seal
from executable_contract import validate_executable_plan_contract


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))


def source(path, pointer):
    return dict(path=path, sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), pointer=pointer)


def migrate(kind):
    origin = 'outputs/source-backed-contract-migration-20261008/fixtures/golden-' + kind + '-plan-v2.json'
    evidence = 'outputs/source-backed-contract-migration-20261008/fixtures/golden-' + kind + '-eligibility-v2.json'
    old = read(origin)['fixture']; item = read(evidence)['fixture']; p = copy.deepcopy(old)
    changes = []

    def change(record, key, value, pointer, refs, reason):
        previous = copy.deepcopy(record.get(key)); record[key] = copy.deepcopy(value)
        if previous != value:
            changes.append(dict(path=pointer, historical_value=previous, value=copy.deepcopy(value),
                                source_evidence=refs, derivation=reason))

    change(p, 'schema_version', '0.3', '/schema_version',
           [source('quantity-eligibility/schemas/quantity-build-plan-v03.schema.json', '')], 'Versioned software contract, not a drawing fact')
    change(p, 'semantic_gate', item['semantic_gate'], '/semantic_gate',
           [source(evidence, '/fixture/semantic_gate')], 'Copy existing full reviewed Gate for identical object')
    # The prior source-backed plan already carries the exact reviewed unit contract.
    factor = p['unit_conversion_contract']['factor']
    if str(p['geometry_basis']['conversion']['factor']) != factor:
        raise ValueError('Cannot migrate a different conversion factor')
    change(p['geometry_basis']['conversion'], 'factor', factor, '/geometry_basis/conversion/factor',
           [source(origin, '/fixture/unit_conversion_contract/factor')], 'Exact decimal representation of the existing physical conversion contract')
    change(p['unit_execution_contract'], 'raw_geometry_conversion', p['geometry_basis']['conversion'],
           '/unit_execution_contract/raw_geometry_conversion',
           [source(origin, '/fixture/geometry_basis/conversion'), source(origin, '/fixture/unit_conversion_contract')],
           'Keep raw audit conversion identical to the exact representation')
    # Existing height conditions explicitly cover this same local route, its slab model and endpoint legs.
    conditions = p['height_evidence']['conditions']
    for name, record in [('base_path', p['base_path'])] + [
            ('owned_adjustments/' + str(i), r) for i, r in enumerate(p['owned_adjustments'])]:
        if record.get('assumption_refs'):
            if record['binding'] != p['height_evidence']['binding']:
                raise ValueError('Conditions cannot transfer across objects')
            change(record, 'conditions', conditions, '/' + name + '/conditions',
                   [source(origin, '/fixture/height_evidence/conditions'), source(origin, '/fixture/' + name),
                    source(origin, '/fixture/assumptions')],
                   'Same explicitly bound Golden slab model/assumptions; retain conditions on each referencing evidence record')
    validate_executable_plan_contract(p); seal(p)
    changes.append(dict(path='/content_hash', historical_value=old['content_hash'], value=p['content_hash'],
                        source_evidence=[source(origin, '/fixture/content_hash')], derivation='Canonical hash of new versioned plan, not modification of historical hash'))
    name = 'golden-' + kind + '-v03.json'
    wrapper = dict(migration_id='pass3-source-backed-' + kind, source_fixture=origin,
        target_fixture=str((OUT / name).relative_to(ROOT)).replace('\\', '/'),
        old_schema_version='0.2', new_schema_version='0.3', migration_tool='pass3-source-migration/1',
        migrated_at=datetime.now(timezone.utc).isoformat(), added_fields=[c['path'] for c in changes],
        source_evidence_for_each_added_field={c['path']: c['source_evidence'] for c in changes},
        field_changes=changes, historical_files_modified=False,
        migration_reason='Builder independently verifies current executable contract; legacy inputs remain unchanged', fixture=p)
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(wrapper, stream, ensure_ascii=False, indent=2)
    return name


def migrate_item(kind):
    origin = 'outputs/source-backed-contract-migration-20261008/fixtures/golden-' + kind + '-eligibility-v2.json'
    plan_path = str((OUT / ('golden-' + kind + '-v03.json')).relative_to(ROOT)).replace('\\', '/')
    old = read(origin)['fixture']; item = copy.deepcopy(old); plan = read(plan_path)['fixture']; changes = []
    def replace(record, key, value, path, pointer):
        if record.get(key) != value:
            changes.append(dict(path=path, historical_value=copy.deepcopy(record.get(key)), value=copy.deepcopy(value),
                source_evidence=[source(plan_path, '/fixture' + pointer)], derivation='Copy already source-backed current execution evidence'))
            record[key] = copy.deepcopy(value)
    for key, plan_key in [('geometry','geometry_basis'), ('base_path','base_path'), ('height','height_evidence'), ('height_requirement','height_requirement')]:
        replace(item, key, plan[plan_key], '/' + key, '/' + plan_key)
    by_id = {r['adjustment_id']: (i, r) for i, r in enumerate(plan['owned_adjustments'])}
    for kind_name, group in item['adjustments'].items():
        for i, record in enumerate(group.get('items', [])):
            j, expected = by_id[record['adjustment_id']]
            if record != expected:
                changes.append(dict(path='/adjustments/' + kind_name + '/items/' + str(i), historical_value=copy.deepcopy(record),
                    value=copy.deepcopy(expected), source_evidence=[source(plan_path, '/fixture/owned_adjustments/' + str(j))],
                    derivation='Same owned physical transition with explicit sourced applicability conditions'))
                group['items'][i] = copy.deepcopy(expected)
    name = 'golden-' + kind + '-eligibility-v3.json'
    wrapper = dict(migration_id='pass3-source-backed-eligibility-' + kind, source_fixture=origin,
        target_fixture=str((OUT / name).relative_to(ROOT)).replace('\\', '/'),
        old_schema_version='input-contract/2', new_schema_version='input-contract/3',
        migration_tool='pass3-source-migration/1', migrated_at=datetime.now(timezone.utc).isoformat(),
        added_fields=[c['path'] for c in changes], source_evidence_for_each_added_field={c['path']: c['source_evidence'] for c in changes},
        field_changes=changes, historical_files_modified=False, migration_reason='Explicit evidence for current executable export', fixture=item)
    with (OUT / name).open('x', encoding='utf-8') as stream: json.dump(wrapper, stream, ensure_ascii=False, indent=2)
    return name


if __name__ == '__main__':
    for kind in ('conduit', 'wire'):
        print(migrate(kind))
        print(migrate_item(kind))
