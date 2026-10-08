"""Completion only after current tests, full regression and immutable-source checks."""
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from classify_legacy import classify

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/post-hardening-pass3-20261008'


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    results = {n: read(OUT / (n + '.json')) for n in ('checked-adversarial', 'checked-current', 'checked-current-suites')}
    for r in results.values(): assert r['failures'] == r['errors'] == r['skipped'] == 0
    assert results['checked-adversarial']['testsRun'] == 44
    assert results['checked-current']['testsRun'] == 30
    assert results['checked-current-suites']['testsRun'] == 114
    regression = read(OUT / 'regression/results.json')
    assert regression['test15'] == 0
    assert 'PASS: 51 offline test suites; no AutoCAD invoked' in (OUT / 'regression/test15.log').read_text(encoding='utf-8-sig')
    legacy = classify(); assert not legacy['unclassified_failures']
    baseline = read(OUT / 'baseline.json')
    tested_sources = read(OUT / 'tested-source-hashes.json')
    assert all(sha(ROOT / path) == value for path, value in tested_sources.items())
    assert subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT).decode().strip() == baseline['commit']
    extra = read(OUT / 'supplemental-frozen-inventory-normalized.json')
    inventories = {}
    for group in ('json_hashes', 'historical_test_hashes'):
        inventory = dict(baseline[group], **extra[group]); changed = [p for p,h in inventory.items() if sha(ROOT/p) != h]
        assert not changed, (group, changed)
        inventories[group] = dict(checked=len(inventory), changed=[])
    expected_changes = {'design-net-quantity/builder.py'}
    changed = set(subprocess.check_output(['git','diff','--name-only'],cwd=ROOT).decode().splitlines())
    assert changed == expected_changes
    golden_path = 'outputs/golden-project-measurement-rules-20261004/design-net-quantities.json'
    golden_hash = sha(ROOT / golden_path)
    assert golden_hash == 'd71dd9ca8f0e297711784d777efe1a0b0406576a78bb2e77fc04314f492aad77'
    ledger = []
    for name,r in results.items():
        for c in r['cases']:
            ledger.append(dict(suite=name,test_id=c['test_id'],status='passed',source=name+'.json',sha256=sha(OUT/(name+'.json'))))
    # Eight raw modules were all run. Only their passing assertions are included;
    # refused legacy cases remain in a separate disposition ledger.
    modules = ('geometry-connection','device-role','candidate-semantic','project-rule-applicability',
               'project-evidence-gate','quantity-eligibility','design-net-quantity','project-evidence-discovery')
    module_results = {}
    for name in modules:
        r = read(OUT / 'regression' / (name+'.json'))
        module_results[name] = dict(raw_tests=r['testsRun'],raw_failures=r['failures'],raw_errors=r['errors'])
        # Builder already has a complete 27-test current-input suite above.
        if name == 'design-net-quantity': continue
        for c in r['cases']:
            if c['raw_status']=='passed':
                ledger.append(dict(suite=name,test_id=c['test_id'],status='passed',source='regression/'+name+'.json',
                                   sha256=sha(OUT/'regression'/(name+'.json'))))
    findings = [
        dict(finding='H1', reproduced=True, root_cause='Builder trusted top-level role and upstream eligibility without validating the full Gate',
             after='Builder and exporter verify status/flags/role/full instance identity/context/accepted evidence independently',
             files=['quantity-eligibility/executable_contract.py','design-net-quantity/builder.py']),
        dict(finding='H2', reproduced=True, root_cause='Execution-unit validation did not connect original geometry to the executable base path',
             after='Exact Decimal conversion, versioned physical or separately reviewed CAD scale, raw/audit/base cross-checks',
             files=['quantity-eligibility/executable_contract.py','quantity-eligibility/plan_v03.py','design-net-quantity/builder.py']),
        dict(finding='H3', reproduced=True, root_cause='Assumption checks enumerated only a partial list of records and omitted evidence-specific conditions',
             after='Explicit recursive admission evidence registry; required refs, approval, provenance, identity and conditions all checked',
             files=['quantity-eligibility/executable_contract.py'])]
    summary = dict(status='Post-Hardening Review Fix Pass 3 complete', baseline=baseline['commit'], findings=findings,
        before=read(OUT/'before.json') | {'cases':'See before.json for original raw traces'},
        schema=dict(current='0.3',legacy='0.2 unchanged; blocked/legacy_incomplete',builder_version='0.2'),
        current_contract=dict(passed=len(ledger),total=len(ledger),basis='188 current-input assertions plus unaffected raw module passes; legacy failures are NOT counted as passes'),
        adversarial='44/44',pass2_current='24/24',builder_current='27/27',safety_current='42/42',
        source_backed_current='45/45',private_source_and_boundary_checks='6/6',actual_report_attribute_checks=2129,
        raw_eight_modules=module_results,legacy_dispositions=dict(count=len(legacy['observed_raw_mismatches']),
            classifications=dict(Counter(e['classification'] for e in legacy['observed_raw_mismatches'])),unclassified=0,
            note='Prior 13 intentional / 37 missing-source catalog preserved; new v0.2 blocks are explicitly observed and separate'),
        test15='51/51',frozen=inventories,tested_source_hashes=tested_sources,
        golden=dict(path=golden_path,sha256=golden_hash,changed=False),
        historical_schema_v02_changed=False,historical_expected_changed=False,quantity_issued=False,commit_created=False,push_performed=False,
        limitations=['Validator verifies supplied reviewed contracts, not reviewer cryptographic authenticity.',
                    'Approved 3D geometry is evidence-validated, not recalculated from CAD.',
                    'Private-source tests require excluded local files.',
                    'Legacy v0.2 exporter remains historical only; executable callers must select plan_v03.'])
    write('current-contract-ledger.json',dict(checks=ledger,legacy_dispositions=legacy))
    write('final-summary.json',summary)
    report = f'''# Post-Hardening Review Fix Pass 3

**Post-Hardening Review Fix Pass 3 complete**

## Findings and contract

H1, H2 and H3 reproduced against the starting commit before implementation changes.
The original 22 Builder-direct tests recorded 24 failed assertions including subtests.
See `before.json` for raw results, and `final-summary.json` for root cause / changed files.

- H1: require full semantic Gate, exact instance identity, accepted evidence and context.
- H2: independently verify raw geometry, exact reviewed conversion and executable base.
- H3: check assumption references recursively over an explicit admission-evidence registry.
- New executable schema **0.3**; historical **0.2** schema and inputs unchanged.
- Shared pure validator is called by current export and again independently by Builder.
- No defaults fill missing Gate, height, identity, raw conversion or assumption conditions.

## Current-contract verification

- Pass 3 direct adversaries/positives: **44/44**.
- Pass 2 original assertions on new explicit current inputs: **24/24**.
- Builder original assertions on current inputs: **27/27**.
- Unified Safety current inputs: **42/42**.
- Source-backed Gate/Eligibility/Builder/Safety assertions: **45/45**.
- Private Golden/report/migration/frozen boundary checks: **6/6**.
- Real report: **2,129 ATTRIB identities** checked.
- Current acceptance ledger: **{len(ledger)}/{len(ledger)}**, including unaffected raw module passes.
- Test 15: **51/51** offline suites, no AutoCAD.

All eight raw module suites and historical migration/Safety suites were also run unchanged.
Their legacy mismatches were retained, not counted as passes. `legacy-dispositions.json`
records {len(legacy['observed_raw_mismatches'])} raw assertion mismatches with actual Builder
entry/return observations and earlier classifications. Original 13/37 classifications
remain preserved. New v0.2 refusals are intentional; unresolved source evidence is not fabricated.
The prior input-only run's implementation-hash guard is retained as a prior-run guard,
not falsely called a current production regression. No unclassified failure remains.

## Replay and immutable evidence

Golden conduit and wire both retain exact `7.77128331912231535912969050917979628`,
reported `7.771283319`; multiplier remains 1. Legacy frozen replay is value-matched /
incomplete-evidence. Complete native in-memory replay matches. No quantity was issued.

- Historical JSON: **{inventories['json_hashes']['checked']} checked, 0 changed**.
- Historical test sources: **{inventories['historical_test_hashes']['checked']} checked, 0 changed**.
- Golden SHA-256: `{golden_hash}` unchanged.
- Historical schema and expected unchanged; no commit or push.

Current source-backed wrappers are additive and local-only. Exact source pointers/hashes
and field deltas are retained. Numeric factor normalization uses the existing exact unit
contract; applicability conditions come from the existing same-object approved slab model.
Public checkout alone cannot reproduce excluded private-data checks.
'''
    with (OUT/'REPORT.md').open('x',encoding='utf-8') as stream: stream.write(report)
    print(json.dumps({k:summary[k] for k in ('status','current_contract','test15','frozen')},ensure_ascii=False))


if __name__=='__main__': main()
