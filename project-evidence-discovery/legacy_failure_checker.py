"""Compare raw unittest outcomes to an explicit ledger; never rewrite outcomes."""
import argparse
import json
import re
from pathlib import Path

def _check_ids(results, ledger):
    """Historical ID-only helper. Not the current acceptance entry."""
    registered={row['test_id']:row for row in ledger['failures']}
    cases={row['test_id']:row['raw_status'] for row in results['cases']}
    failed={key for key,value in cases.items() if value in ('failure','error')}
    unexpected=sorted(failed-registered.keys())
    changed=sorted(key for key in registered if cases.get(key) not in ('failure','error'))
    return {'accepted':not unexpected and not changed,
            'unclassified_failures':unexpected,'registered_outcome_changed':changed,
            'classified_failures':[registered[key] for key in sorted(failed & registered.keys())],
            'failures_counted_as_passed':0}

def check(results,ledger):
    if ledger.get('version')=='2':return check_current(results,ledger)
    result=_check_ids(results,ledger)
    result['acceptance_contract']='legacy_id_only_not_current'
    return result

CLASSIFICATIONS={
    'A':'intentional_legacy_rejection',
    'B':'legacy_fixture_missing_current_contract_fields',
    'C':'historical_diagnostic_regression_currently_repaired',
}

def normalized_failure_reason(case):
    trace=case.get('traceback','')
    frames=re.findall(r'File "[^"]+", line \d+, in (\w+)',trace)
    if frames and frames[-1]!=case['test_id'].split('.')[-1]:return 'unregistered_failure_site'
    last_frame=re.split(r'File "[^"]+", line \d+, in \w+',trace)[-1]
    if re.search(r'^IndexError:\s*list index out of range\s*$',trace,re.M) and re.search(r"\[['\"]bindings['\"]\]\[0\]",last_frame):
        return 'binding_candidate_absent'
    if re.search(r"AssertionError:\s*['\"]unresolved['\"]\s*!=\s*['\"]supported['\"]",trace):return 'unresolved_not_supported'
    if re.search(r"AssertionError:\s*['\"]unresolved['\"]\s*!=\s*['\"]conflicting['\"]",trace):return 'unresolved_not_conflicting'
    if re.search(r'AssertionError:\s*0\s*!=\s*1',trace) and re.search(r"len\(\w+\[['\"]bindings['\"]\]\)",last_frame):return 'binding_count_zero_not_one'
    return 'unregistered_failure_reason'

def check_current(results,ledger):
    result=_check_ids(results,ledger)
    mismatches=[]
    if ledger.get('version')!='2':mismatches.append({'reason':'current_ledger_v2_required'})
    registered={r['test_id']:r for r in ledger['failures']}
    if len(registered)!=len(ledger['failures']):mismatches.append({'reason':'duplicate_registered_test_id'})
    for row in ledger['failures']:
        if row.get('category') not in CLASSIFICATIONS or row.get('classification')!=CLASSIFICATIONS.get(row.get('category')):
            mismatches.append({'test_id':row['test_id'],'reason':'classification_mismatch'})
    for case in results['cases']:
        if case['test_id'] not in registered or case['raw_status'] not in ('failure','error'):continue
        actual=normalized_failure_reason(case);expected=registered[case['test_id']].get('normalized_reason')
        if actual!=expected:mismatches.append({'test_id':case['test_id'],'expected':expected,'actual':actual})
    result['normalized_reason_mismatches']=mismatches
    result['accepted']=result['accepted'] and not mismatches
    result['acceptance_contract']='legacy_failure_ledger/2'
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('results');p.add_argument('ledger');p.add_argument('output');a=p.parse_args()
    result=check_current(json.loads(Path(a.results).read_text(encoding='utf-8-sig')),
                 json.loads(Path(a.ledger).read_text(encoding='utf-8-sig')))
    with Path(a.output).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    raise SystemExit(0 if result['accepted'] else 1)
