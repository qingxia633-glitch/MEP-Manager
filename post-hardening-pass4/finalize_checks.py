"""Record actual results; never convert legacy assertion failures into passes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/post-hardening-pass4-20261009'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, value):
    with (OUT/name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)

def main():
    baseline = read(OUT/'baseline.json')
    prior = ROOT/'outputs/post-hardening-pass3-20261008'
    inventories = {'pass4_artifacts': baseline['hashes'], 'pass4_test_sources': baseline['tests']}
    old, extra = read(prior/'baseline.json'), read(prior/'supplemental-frozen-inventory-normalized.json')
    for group in ('json_hashes', 'historical_test_hashes'):
        inventories[group] = dict(old[group], **extra[group])
    frozen = {}
    for name, files in inventories.items():
        changed = [p for p,h in files.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
        frozen[name] = {'checked':len(files),'changed':changed}
        assert not changed, (name,changed)
    assert sha(ROOT/'README.md') == baseline['readme_hash'], 'Pre-existing README changed'
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    assert head == baseline['head']
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    golden = ROOT/'outputs/golden-project-measurement-rules-20261004/design-net-quantities.json'
    assert sha(golden)=='d71dd9ca8f0e297711784d777efe1a0b0406576a78bb2e77fc04314f492aad77'
    test15 = read(OUT/'test15-result.json')
    assert 'PASS: 51 offline test suites; no AutoCAD invoked' in (OUT/'test15.log').read_text(encoding='utf-8-sig')
    direct, current = read(OUT/'final-pass4.json'), read(OUT/'final-current.json')
    assert direct['testsRun']==45 and direct['failures']==direct['errors']==0
    remaining=[]
    for case in current['cases']:
        if case['raw_status']=='passed': continue
        refusals=[x for x in case['builder_admission_observations'] if x['status']=='contract_violation']
        assert refusals and all(any('provenance' in r or 'source hash/status/evidence binding' in r
            for r in x['blocking_reasons']) for x in refusals), case
        remaining.append({'test_id':case['test_id'],'raw_status':case['raw_status'],
            'classification':'legacy_inline_provenance_incomplete', 'observed_refusals':refusals,
            'historical_expected_changed':False,
            'current_positive_counterparts':'post-hardening-pass4/tests/test_contracts.py'})
    assert len(remaining)==10
    write('legacy-inline-dispositions.json',{'cases':remaining,'counted_as_passes':False})
    summary={'head':head,'contracts':{'plan':'0.3','subcontracts':'authorization/provenance/assumptions version 1'},
        'pass4':'45/45','current_existing_assertions':{'run':182,'passed':172,'failures':6,'errors':4,
            'disposition':'10 legacy inline provenance refusals, NOT counted as passes'},
        'pass3':'42/44; 2 legacy inline provenance refusals',
        'pass2':'20/24; 4 legacy inline provenance refusals',
        'builder':'27/27','safety':'38/42; 4 legacy inline provenance refusals',
        'source_backed':'45/45','real_report_attribute_checks':2129,
        'test15':test15,'test15_suites':'51/51','frozen':frozen,
        'golden_sha256':sha(golden),'golden_changed':False,'readme_user_edit_preserved':True,
        'historical_expected_modified':False,'official_quantity_issued':False,'commit_created':False,
        'push_performed':False,'all_historical_assertions_green':False,
        'limitations':['Structural consistency validates supplied audit contracts, not cryptographic reviewer authenticity.',
            'Source-backed adapter verifies file hashes/pointers; archived approvals remain archived evidence, not new drawing facts.',
            'Raw historical regression mismatches are preserved in regression-1; no wholesale all-green claim.']}
    write('final-summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
