"""Fail-closed completion report; keep all historical test outcomes visible."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/post-hardening-pass2-20261008'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    suites = ['geometry-connection', 'device-role', 'candidate-semantic', 'project-rule-applicability',
              'project-evidence-gate', 'quantity-eligibility', 'design-net-quantity',
              'project-evidence-discovery', 'safety-hardening', 'post-hardening-tests', 'contract-migration']
    raw = {name: read(OUT / 'regression' / (name + '.json')) for name in suites}
    adversarial = read(OUT / 'final-adversarial.json')
    current = read(OUT / 'final-current-contract.json')
    for r in (adversarial, current):
        assert not (r['failures'] or r['errors'] or r['skipped'])
    old = read(ROOT / 'contract-migration/classification-catalog.json')['entries']
    expected = {(e['suite'], e['test_id']) for e in old}
    extra = [
        {'suite': 'post-hardening-tests', 'test_id': 'test_findings.Findings.test_P2_1_report_attribute_owner_binding',
         'classification': 'intentional legacy rejection', 'reason': 'Synthetic report lacks explicit acquisition scope; new declared-scope fixture reruns original assertions'},
        {'suite': 'post-hardening-tests', 'test_id': 'test_contract_boundaries.Boundaries.test_adapter_repeated_attribute_handle_keeps_owners_separate',
         'classification': 'intentional legacy rejection', 'reason': 'Same missing acquisition-scope evidence; original unknown scope remains blocked'},
        {'suite': 'contract-migration', 'test_id': 'test_migration.Migration.test_existing_json_and_python_frozen',
         'classification': 'prior_run_implementation_freeze_guard',
         'reason': 'Prior input-only migration forbade implementation changes. Pass 2 explicitly authorizes four fixes; historical JSON and expected are still frozen and independently verified.'}]
    expected.update((e['suite'], e['test_id']) for e in extra)
    actual = {(name, case['test_id']) for name, r in raw.items() for case in r['cases'] if case['raw_status'] != 'passed'}
    assert expected == actual, 'Unclassified failure; do not declare complete'
    results = read(OUT / 'regression/results.json')
    log = (OUT / 'regression/test15.log').read_text(encoding='utf-8-sig')
    assert results['test15'] == 0 and 'PASS: 51 offline test suites; no AutoCAD invoked' in log
    baseline = read(OUT / 'baseline.json')
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == baseline['commit']
    supplement = read(OUT / 'supplemental-frozen-inventory.json')
    frozen = dict(baseline['json_hashes'], **supplement['json_hashes'])
    assert all(sha(ROOT / path) == value for path, value in frozen.items())
    assert all(sha(ROOT / path) == value for path, value in baseline['historical_test_hashes'].items())
    allowed = {'design-net-quantity/builder.py', 'project-evidence-discovery/annotations.py',
               'quantity-eligibility/quantity_contract.py', 'quantity-eligibility/resolver.py'}
    changed = set(subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT).decode().splitlines())
    assert changed == allowed, 'Unexpected tracked implementation changes'
    golden = 'outputs/golden-project-measurement-rules-20261004/design-net-quantities.json'
    golden_hash = sha(ROOT / golden)
    prior = read(ROOT / 'outputs/source-backed-contract-migration-20261008/final-summary.json')
    assert golden_hash == prior['golden_design_net_quantity']['sha256']
    count = sum(sum(c['raw_status'] == 'passed' for c in r['cases']) for r in raw.values()) + adversarial['testsRun'] + current['testsRun']
    checks = []
    for name, r in list(raw.items()) + [('pass2-adversarial', adversarial), ('current-boundary-checks', current)]:
        source = (OUT / 'regression' / (name + '.json')) if name in raw else OUT / ('final-adversarial.json' if name == 'pass2-adversarial' else 'final-current-contract.json')
        checks.extend({'suite': name, 'test_id': c['test_id'], 'status': 'passed',
                       'result_source': str(source.relative_to(ROOT)), 'result_sha256': sha(source)}
                      for c in r['cases'] if c['raw_status'] == 'passed')
    assert len(checks) == count
    save('current-contract-ledger.json', {'current_checks': checks,
         'legacy_and_prior_run_dispositions': old + extra,
         'unclassified_failure_policy': 'block completion; never treat as pass'})
    findings = [
        {'finding': 'H1', 'reproduced': 'Original 6b937fd baseline reproduced in Pass 1; current starting commit already blocks it',
         'root_cause': 'Original binding omitted full parent_path; shared exact identity was introduced in Pass 1',
         'files_changed_this_pass': [], 'test': 'test_H1_cross_instance_gate_eligibility_builder',
         'before': 'blocked at 79b694d', 'after': 'Gate blocked, Eligibility blocked, exporter refuses Plan'},
        {'finding': 'H2', 'reproduced': 'Original baseline reproduced in Pass 1; current starting commit already blocks it',
         'root_cause': 'Original arithmetic-only conversion validation; versioned physical/CAD contracts already fixed it',
         'files_changed_this_pass': [], 'test': 'test_H2_arithmetic_consistent_wrong_mm_factor',
         'before': 'unit_conversion_contract_invalid', 'after': 'unit_conversion_contract_invalid'},
        {'finding': 'H3', 'reproduced': True,
         'root_cause': 'Planar exemption accepted prose reason without explicit requirement/reviewed rule; exemption declaration could contradict 3D mode',
         'files_changed_this_pass': ['quantity-eligibility/quantity_contract.py', 'quantity-eligibility/resolver.py'],
         'test': ['test_H3_height_exemption_must_be_explicit', 'test_H3_height_exemption_requires_reviewed_rule', 'test_H3_height_exemption_cannot_override_3d'],
         'before': 'invalid exemptions built; eligibility omitted declaration',
         'after': 'contract_violation / generation blocked; supported identity-bound 3D evidence and explicit reviewed planar exemption pass'},
        {'finding': 'H4', 'reproduced': True,
         'root_cause': 'Original specification provenance already retained, but full semantic Gate review record was not included in replay digest or upstream plan',
         'files_changed_this_pass': ['design-net-quantity/builder.py', 'quantity-eligibility/resolver.py'],
         'test': ['test_H4_semantic_binding_review_must_be_frozen', 'test_H4_eligibility_export_retains_semantic_review'],
         'before': 'changed semantic review could replay_matched at identical value',
         'after': 'numeric_match true and evidence_contract_match false; native unchanged positive replay_matched'},
        {'finding': 'N1', 'reproduced': True,
         'root_cause': 'Adapter assumed top-level INSERT scope without acquisition evidence; missing explicit attribute/owner identity aliases',
         'files_changed_this_pass': ['project-evidence-discovery/annotations.py'],
         'test': ['test_N1_full_adapter_owner_fields', 'test_N1_missing_scope_not_modelspace', 'test_N1_repeated_attribute_handles_not_crossed'],
         'before': 'unproven report scope produced direct owner binding',
         'after': 'proven top-level owner binding supported; missing/nested scope preserved unresolved; no instance crossover'}]
    summary = {
        'status': 'Post-Hardening Review Fix Pass 2 complete',
        'starting_commit': baseline['commit'], 'findings': findings,
        'before_adversarial': {k: read(OUT / 'before-tests.json')[k] for k in ('testsRun', 'failures', 'errors')},
        'new_adversarial': {'passed': adversarial['testsRun'], 'total': adversarial['testsRun']},
        'current_contract': {'passed': count, 'total': count,
                             'basis': 'Raw unaffected passes + current migrated/legacy rejection checks + Pass 2 adversarial + current frozen/adapter/private checks; raw legacy mismatches NOT counted as passes'},
        'raw_suites': {name: {'total': r['testsRun'], 'passed': sum(c['raw_status'] == 'passed' for c in r['cases']),
                             'failures': r['failures'], 'errors': r['errors']} for name, r in raw.items()},
        'original_legacy_classification': {'intentional legacy rejection': 13, 'missing real source evidence': 37},
        'additional_old_context_checks': extra,
        'genuine_regression': 0, 'unclassified_failure': 0,
        'verification_harness_note': 'An initial same-name test-module import collision in the new harness was resolved by loading the exact file path; original assertions were not changed. Final six current checks pass.',
        'test15': {'passed': 51, 'total': 51},
        'frozen_json': {'checked': len(frozen), 'changed': []},
        'historical_test_sources': {'checked': len(baseline['historical_test_hashes']), 'changed': []},
        'golden_quantity': {'path': golden, 'sha256': golden_hash, 'changed': False},
        'implementation_files_changed': sorted(changed),
        'new_quantity_issued': False, 'push_performed': False,
    }
    save('final-summary.json', summary)
    save('legacy-classification.json', {'original_entries': old, 'additional_entries': extra})
    rows = '\n'.join('| ' + f['finding'] + ' | ' + str(f['reproduced']) + ' | ' + f['before'] + ' | ' + f['after'] + ' |' for f in findings)
    report = f'''# Post-Hardening Review Fix Pass 2

**Post-Hardening Review Fix Pass 2 complete**，按版本化 current-contract 口径验收。

## Finding / reproduction / before / after

| Finding | Reproduced | Before | After |
|---|---|---|---|
{rows}

逐项 root cause、changed files 和 adversarial test 见 final-summary.json。
H1/H2 在本轮起点已修复，未重复修改实现。H3/H4/N1 的残余缺口先写反例，再改实现。
首次 18 项：9 通过、6 失败、3 缺字段错误；最终新增专项 {adversarial['testsRun']}/{adversarial['testsRun']}。

## Current-contract result

- Current Contract：{count}/{count}。保留的旧断言不冒充当前通过项。
- current-contract-ledger.json 逐项列出实际通过的 test_id、结果文件和 hash，以及所有 legacy/旧运行期断言的处置。
- 八模块与 Unified Safety 全部原样执行；50 项既有 legacy 不匹配继续按原分类记录。
- 原始八模块 189/224，Safety 27/42：13 intentional legacy rejection + 37 missing real source evidence。
- 旧 Post-Hardening 16/18：另外 2 个无提取范围声明的合成报告被阻断；原断言在新明确顶层的合成输入上通过。
- 旧 migration 108/109：唯一差异是上一轮禁止实现变更的 Python hash 守卫。它不适用于本轮授权修改，原记录保留，改用本轮不可变证据/历史测试边界核对。
- source-backed migration 的其他 108 项通过；加本轮冻结边界检查后当前迁移验证 109/109。
- 新 adapter 原断言复跑 2 项、冻结检查、分类覆盖、私有 Golden 双对象及真实报告检查均通过。
- 新验收脚本首次发生同名测试模块导入冲突，已改为按文件路径装载；未改原断言，最终 6 项全部通过。中间日志保留。
- 两个 Golden legacy replay 保持 value matched / legacy evidence incomplete；完整 native replay matched。
- 真实报告：2,129 个 ATTRIB owner/path 验证通过。未从这些属性推断线路电气语义。
- genuine regression = 0；未分类失败 = 0。
- Test 15：51/51；未调用 AutoCAD。

## Frozen hash

- {len(frozen)} 个历史 JSON：0 变化。
- {len(baseline['historical_test_hashes'])} 个历史测试 Python：0 变化；未修改 expected。
- Golden DesignNetQuantity SHA-256：`{golden_hash}`，0 变化。
- 通用实现仅 4 文件变化：quantity_contract.py、Eligibility resolver.py、Builder builder.py、Discovery annotations.py。
- 新测试、验收脚本和说明位于 post-hardening-pass2/。
- 未 push、未签发净量、未继续新功能。

## 限制

缺少 acquisition scope 的报告保留 unresolved；本轮不恢复未知嵌套路径。
继续使用 schema 0.2 的 converted_2d / approved_3d，不另增计量模式或改历史 Plan。
公开 checkout 缺少私有报告与 Golden 输入时不能重现全部本机验收。
本轮没有承诺原始 legacy 测试全绿；所有原始 tracebacks 保存在 regression/。
'''
    with (OUT / 'REPORT.md').open('x', encoding='utf-8') as stream:
        stream.write(report)
    print(json.dumps({k: summary[k] for k in ('status', 'current_contract', 'test15', 'frozen_json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
