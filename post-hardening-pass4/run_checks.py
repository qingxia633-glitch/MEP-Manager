"""New outputs only. Preserve raw suites and expected; never classify by exit alone."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/post-hardening-pass4-20261009'


if __name__=='__main__':
    name=sys.argv[1]
    suites=[('pass4','post-hardening-pass4/tests'),('pass3','post-hardening-pass3/tests'),
            ('geometry','geometry-connection/tests'),('device','device-role/tests'),
            ('candidate','candidate-semantic/tests'),('applicability','project-rule-applicability/tests'),
            ('gate','project-evidence-gate/tests'),('eligibility','quantity-eligibility/tests'),
            ('builder','design-net-quantity/tests'),('discovery','project-evidence-discovery/tests'),
            ('safety','safety-hardening'),('source-backed','contract-migration/tests')]
    output=OUT/name;output.mkdir(exist_ok=False)
    env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    results={}
    for label,folder in suites:
        with (output/(label+'.log')).open('x',encoding='utf-8') as f:
            r=subprocess.run([sys.executable,'-B','contract-migration/run_suite.py',folder,str(output/(label+'.json'))],
                             stdout=f,stderr=subprocess.STDOUT,env=env,cwd=ROOT)
        results[label]=r.returncode
        print(label,r.returncode,flush=True)
    with (output/'exits.json').open('x',encoding='utf-8') as f:json.dump(results,f,indent=2)
