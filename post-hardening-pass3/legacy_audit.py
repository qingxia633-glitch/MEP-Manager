"""Observe actual Builder rejections during unchanged legacy tests; never alter outcomes."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'contract-migration'))
from run_suite import Recorded


class Observed(Recorded):
    def startTest(self, test):
        self.returns = []
        super().startTest(test)
        sys.setprofile(self.observe)

    def observe(self, frame, event, value):
        if event == 'return' and frame.f_code.co_name == '_execute' and Path(frame.f_code.co_filename).resolve() == ROOT / 'design-net-quantity/builder.py':
            p = frame.f_locals.get('p')
            self.returns.append(dict(schema_version=p.get('schema_version') if isinstance(p, dict) else None,
                status=value.get('status') if isinstance(value, dict) else None,
                blocking_reasons=value.get('blocking_reasons') if isinstance(value, dict) else None))

    def stopTest(self, test):
        sys.setprofile(None)
        self.cases[-1]['builder_admission_observations'] = self.returns
        super().stopTest(test)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(sys.argv[1])
    result = unittest.TextTestRunner(verbosity=1, resultclass=Observed).run(suite)
    with Path(sys.argv[2]).open('x', encoding='utf-8') as stream:
        json.dump(dict(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
            skipped=len(result.skipped), cases=result.cases), stream, ensure_ascii=False, indent=2)
    sys.exit(0 if result.wasSuccessful() else 1)
