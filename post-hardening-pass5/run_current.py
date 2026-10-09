"""Run unchanged current-input Builder/source-backed assertions, no result filtering."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'post-hardening-pass4'))
sys.path.insert(0,str(ROOT/'contract-migration'))
from run_suite import Recorded
import current_checks

if __name__=='__main__':
    names=unittest.defaultTestLoader.getTestCaseNames(current_checks.Current)
    selected=[n for n in names if n.startswith(('test_Builder_', 'test_SourceBacked'))]
    suite=unittest.TestSuite(current_checks.Current(n) for n in selected)
    r=unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(suite)
    with Path(sys.argv[1]).open('x',encoding='utf-8') as f:
        json.dump(dict(testsRun=r.testsRun,failures=len(r.failures),errors=len(r.errors),cases=r.cases),f,indent=2)
    sys.exit(0 if r.wasSuccessful() else 1)
