"""Classify only observed, explained rejections; unexplained failures stop acceptance."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/post-hardening-pass3-20261008'


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def classify():
    original = read(ROOT / 'contract-migration/classification-catalog.json')['entries']
    known = {(e['suite'], e['test_id']): e for e in original}
    prior = read(ROOT / 'outputs/post-hardening-pass2-20261008/legacy-classification.json')['additional_entries']
    known.update({(e['suite'], e['test_id']): e for e in prior})
    entries = []
    for path in sorted((OUT / 'observed-legacy').glob('*.json')):
        for case in read(path)['cases']:
            if case['raw_status'] == 'passed': continue
            key = path.stem, case['test_id']; observations = case['builder_admission_observations']
            if key in known:
                reason = 'Retained prior explicit classification'
                category = known[key]['classification']
            elif observations and all(o['schema_version'] == '0.2' and o['status'] == 'blocked' and
                    any('legacy_incomplete' in s for s in o['blocking_reasons']) for o in observations):
                trace = case['traceback']
                assert ("AssertionError: 'blocked' !=" in trace or "KeyError: 'quantity'" in trace or
                        "KeyError: 'numeric_match'" in trace), ('Unexpected failure after rejection', key)
                category = 'intentional legacy rejection'
                reason = 'Observed Builder rejected historical v0.2 before quantity execution; old assertion expected executable v0.2 output'
            else:
                raise AssertionError(('Unclassified failure', key, observations))
            entries.append(dict(suite=path.stem, test_id=case['test_id'], classification=category,
                reason=reason, raw_status=case['raw_status'], observed_builder_returns=observations,
                result_source=str(path.relative_to(ROOT)).replace('\\', '/')))
    return dict(original_classification_catalog_preserved=original, observed_raw_mismatches=entries,
                unclassified_failures=[], historical_expected_modified=False)


if __name__ == '__main__':
    result = classify()
    with (OUT / 'legacy-dispositions.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(len(result['observed_raw_mismatches']))
