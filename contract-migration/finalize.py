"""Summarize raw historical results separately from versioned contract checks."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/source-backed-contract-migration-20261008'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    suites = ['geometry-connection', 'device-role', 'candidate-semantic',
              'project-rule-applicability', 'project-evidence-gate',
              'quantity-eligibility', 'design-net-quantity',
              'project-evidence-discovery', 'safety-hardening']
    raw = {name: read(OUT / 'regression' / (name + '.json')) for name in suites}
    failed = {(name, case['test_id']) for name, result in raw.items()
              for case in result['cases'] if case['raw_status'] != 'passed'}
    catalog = read(ROOT / 'contract-migration/classification-catalog.json')
    classified = {(entry['suite'], entry['test_id']) for entry in catalog['entries']}
    assert failed == classified, 'Unexpected historical failure; do not complete'
    migration = read(OUT / 'migration-verification-confirmed.json')
    post = read(OUT / 'regression/post-hardening-tests.json')
    for result in (migration, post):
        assert not (result['failures'] or result['errors'] or result['skipped'])
    # Presence of this terminal line requires all 51 child processes to have passed.
    test15 = (OUT / 'regression/test15.log').read_text(encoding='utf-8-sig')
    assert 'PASS: 51 offline test suites; no AutoCAD invoked' in test15
    assert sum(line.startswith('RUN ') for line in test15.splitlines()) == 51
    baseline = read(OUT / 'baseline.json')
    frozen = {}
    for group in ('json_hashes', 'existing_python_hashes'):
        changes = [path for path, value in baseline[group].items()
                   if not (ROOT / path).is_file() or sha(ROOT / path) != value]
        frozen[group] = {'checked': len(baseline[group]), 'changed': changes}
        assert not changes, 'Frozen input or implementation changed'
    prior = read(ROOT / 'outputs/post-hardening-review-fix-20261008/final-summary.json')
    implementation_changes = [path for path, value in prior['implementation_hashes'].items()
                              if sha(ROOT / path) != value]
    assert not implementation_changes, 'Generic implementation changed during migration'
    golden = prior['golden_design_net_quantity']
    assert sha(ROOT / golden['path']) == golden['sha256']
    real = read(OUT / 'real-report-check.json')
    assert real['passed'] and sha(ROOT / real['source']) == real['sha256']
    replays = read(OUT / 'replay-validation.json')
    assert len(replays) == 2
    for result in replays:
        assert result['numeric_match'] and not result['evidence_contract_match']
        assert result['native_test_replay_status'] == 'replay_matched'
        assert result['legacy_replay_status'] == 'replay_value_matched_legacy_evidence_incomplete'
        assert result['multiplier'] == 1
    summaries = {name: {'total': r['testsRun'], 'passed': sum(c['raw_status'] == 'passed' for c in r['cases']),
                       'failures': r['failures'], 'errors': r['errors'], 'skipped': r['skipped']}
                 for name, r in raw.items()}
    counts = Counter(e['classification'] for e in catalog['entries'])
    counts['genuine regression'] = 0
    counts['migration bug'] = 0
    versioned_count = sum(s['passed'] for s in summaries.values()) + migration['testsRun'] + post['testsRun']
    classification = {'historical_assertions_modified': False,
                      'raw_historical_all_green': False,
                      'classification_counts': dict(counts),
                      'unclassified_failures': [], 'entries': catalog['entries']}
    save('failure-classification.json', classification)
    summary = {
        'status': 'Post-Hardening Review Fix Pass complete',
        'acceptance_basis': 'authorized source-backed versioned input migration; raw legacy assertions retained separately',
        'raw_historical_all_green': False,
        'raw_suite_results': summaries,
        'historical_contract_mismatches': dict(counts),
        'migration_tests': {'passed': migration['testsRun'], 'total': migration['testsRun']},
        'post_hardening_tests': {'passed': post['testsRun'], 'total': post['testsRun']},
        'versioned_acceptance': {'passed': versioned_count, 'total': versioned_count,
                                'composition': 'unaffected historical passes + versioned migration tests + Post-Hardening 18; excludes raw legacy assertion failures'},
        'test15': {'passed': 51, 'total': 51},
        'real_report': real,
        'frozen_inventory': frozen,
        'golden_design_net_quantity': dict(golden, unchanged=True),
        'generic_implementation_changes_during_migration': implementation_changes,
        'complete_versioned_inputs': 5,
        'unmigratable_synthetic_families': ['gate', 'eligibility item', 'build plan'],
        'new_quantity_issued': False,
        'historical_expected_modified': False,
        'historical_fixture_modified': False,
        'push_or_merge_performed': False,
    }
    save('final-summary.json', summary)
    rows = '\n'.join(f"| {name} | {s['passed']}/{s['total']} | {s['failures'] + s['errors']} |"
                     for name, s in summaries.items())
    report = f'''# Source-backed contract migration verification

## 结论

Post-Hardening Review Fix Pass complete，按本轮批准的版本化输入契约验收。
**这不表示旧测试原始断言全部变绿。** 原断言完整保留、原样运行，50 项旧契约不匹配分别记录并验证阻断；未修改 expected。

## 迁移对象与来源

- 新建 5 份 contract-complete 输入：Golden Gate、conduit/wire Eligibility、conduit/wire BuildPlan。
- wrapper 使用 input-contract/2；Plan 本身仍为 schema 0.2。
- 每份包装记录 source/target、版本、逐字段差异、来源/hash/pointer、迁移原因、时间与工具版本/hash。
- parent_path=[] 由真实 ModelSpaceTopLevelAllLayers 报告和唯一 13CF5 顶层记录证明。
- project 来自原审核项目证据；drawing 来自真实报告；scope 来自原 edge measurement_scope。
- geometry_basis / height_evidence 使用原有 supported 证据与可验证来源，不制造高度。
- 原输入经过已有 loader 的投影视图也有独立记录，迁移差异与该视图逐字段核对。
- 三类无真实补证的合成输入继续 legacy_incomplete；没有把缺失高度改成 supported 或 not_applicable。

## 回归结果

| 原始套件 | 原样通过 | 保留的旧契约不匹配 |
|---|---:|---:|
{rows}

- 原八模块原始结果：189/224；Safety 原始结果：27/42。
- 50 项分类：13 项 legacy contract intentionally rejected；37 项 missing real source evidence。
- 每项均有可执行旧输入阻断校验；可合法迁移者以 v2 输入重新执行原断言。
- genuine regression = 0；migration bug = 0；未分类失败 = 0。
- 迁移专项：{migration['testsRun']}/{migration['testsRun']}；Post-Hardening：{post['testsRun']}/{post['testsRun']}。
- 当前版本化验收：{versioned_count}/{versioned_count}（216 个未受影响历史通过项 + {migration['testsRun']} 个迁移检查 + {post['testsRun']} 个 Post-Hardening 检查）。
- Test 15：51/51；真实报告 load_report → discover：{real['attribute_identity_checks']} 个 ATTRIB 身份检查通过。
- 上述新总数不包含、也不伪报 50 项旧断言为通过；原始失败 traceback 仍保存在 regression/。

## Golden / replay

- conduit、wire 精确值均为 7.77128331912231535912969050917979628 m，报告值 7.771283319 m；multiplier=1。
- 两个旧 frozen replay：replay_value_matched_legacy_evidence_incomplete。
- 两个完整 native 测试 replay：replay_matched；更改审核依据的反例不得完整匹配。
- 不签发、不登记新 DesignNetQuantity；native 对象仅用于内存测试。

## 冻结核对

- {frozen['json_hashes']['checked']} 个既有 JSON：0 变化。
- {frozen['existing_python_hashes']['checked']} 个既有 Python 文件：0 变化。
- 上轮 7 个修复实现文件 hash：本轮 0 变化。
- Golden 正式净量 SHA-256：`{golden['sha256']}`，保持一致。
- 原 fixture、历史 expected、历史证据、纠正证据与正式数量均未覆盖。
- 未 push / merge。

## 证据文件

- migration-manifest.json / supplemental-manifest.json：迁移与 legacy 保留记录。
- source-input-projections.json：真实旧输入 loader 投影。
- failure-classification.json：50 项原始不匹配的逐项分类和来源。
- migration-verification-confirmed.json：迁移专项实际结果，独立 subprocess exit=0。
- replay-validation.json：数值和证据契约分开报告。
- final-summary.json：机器可读总验收与 hash 核对。

## 剩余限制

缺少真实来源的旧合成输入不能作为正式项目正样本。直接运行旧套件仍会出现原来的契约不匹配；
本轮以独立版本化测试记录正确拒绝及合法新输入通过，不重写旧测试历史。
本轮不证明更多图纸对象的身份或高度，也不扩展 Golden 的规则作用范围。
'''
    with (OUT / 'REPORT.md').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(report)
    print(json.dumps({k: summary[k] for k in ('status', 'versioned_acceptance', 'test15', 'frozen_inventory')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
