"""Read-only frozen checks; writes only a new Pass 5 result artifact."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/post-hardening-pass5-20261009'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    baseline=read(OUT/'baseline.json')
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==baseline['head']
    checks={}
    for group in ('files','tests'):
        changed=[p for p,h in baseline[group].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
        checks[group]=dict(count=len(baseline[group]),changed=changed)
        assert not changed,checks
    assert sha(ROOT/'README.md')==baseline['readme_hash']
    prior=ROOT/'outputs/post-hardening-pass3-20261008'
    a,b=read(prior/'baseline.json'),read(prior/'supplemental-frozen-inventory-normalized.json')
    for group in ('json_hashes','historical_test_hashes'):
        inventory=dict(a[group],**b[group])
        changed=[p for p,h in inventory.items() if sha(ROOT/p)!=h]
        checks[group]=dict(count=len(inventory),changed=changed)
        assert not changed
    golden=ROOT/'outputs/golden-project-measurement-rules-20261004/design-net-quantities.json'
    assert sha(golden)=='d71dd9ca8f0e297711784d777efe1a0b0406576a78bb2e77fc04314f492aad77'
    tests={}
    for name,total in [('after',11),('pass4',45),('current',72)]:
        r=read(OUT/(name+'.json'));assert r['testsRun']==total and r['failures']==r['errors']==0
        tests[name]=dict(run=r['testsRun'],failures=r['failures'],errors=r['errors'])
    assert read(OUT/'test15-result.json')['exit_code']==0
    assert 'PASS: 51 offline test suites; no AutoCAD invoked' in (OUT/'test15.log').read_text(encoding='utf-8-sig')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    before=read(OUT/'before.json')
    summary=dict(status='Post-Hardening Review Fix Pass 5 complete',baseline=baseline['head'],
        reproduced=before['failures']==1 and before['errors']==0,
        before=dict(run=before['testsRun'],failures=before['failures'],errors=before['errors']),
        current=tests,test15='51/51',frozen=checks,golden_sha256=sha(golden),
        historical_expected_changed=False,quantity_issued=False,commit_created=False,push_performed=False,
        scope='Conditional provenance root admission only; no broad code review or legacy expectation changes')
    with (OUT/'final-summary.json').open('x',encoding='utf-8') as f:json.dump(summary,f,ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
