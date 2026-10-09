"""Run unchanged historical suites and record outcomes; never rewrite expectations."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/post-hardening-pass3-20261008/regression'
SUITES = ['geometry-connection', 'device-role', 'candidate-semantic',
          'project-rule-applicability', 'project-evidence-gate', 'quantity-eligibility',
          'design-net-quantity', 'project-evidence-discovery', 'safety-hardening',
          'post-hardening-tests', 'contract-migration', 'post-hardening-pass2', 'post-hardening-pass3']


if __name__ == '__main__':
    OUT.mkdir(exist_ok=False)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    results = {}
    for name in SUITES:
        tests = name if name in ('safety-hardening', 'post-hardening-tests') else name + '/tests'
        with (OUT / (name + '.log')).open('x', encoding='utf-8') as log:
            r = subprocess.run([sys.executable, '-B', 'contract-migration/run_suite.py', tests,
                                str(OUT / (name + '.json'))], cwd=ROOT, env=env,
                               stdout=log, stderr=subprocess.STDOUT)
        results[name] = r.returncode
        print(name, r.returncode, flush=True)
    # Use the installed PowerShell 7 supplied explicitly at invocation.
    shell = Path(sys.argv[1])
    env['PATH'] = str(shell.parent) + os.pathsep + env['PATH']
    with (OUT / 'test15.log').open('x', encoding='utf-8') as log:
        r = subprocess.run([str(shell), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                            'model-core/tests/Run-Regressions.ps1'], cwd=ROOT, env=env,
                           stdout=log, stderr=subprocess.STDOUT)
    results['test15'] = r.returncode
    with (OUT / 'results.json').open('x', encoding='utf-8') as stream:
        json.dump(results, stream, indent=2)
    print(results, flush=True)
