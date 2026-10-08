"""Original assertions on separately declared v0.3 inputs, never altered results."""
import copy
import json
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'post-hardening-pass3'))
from current_checks import new, synthetic_item, current_loader, OUT, read


def project_plan(kind='conduit'):
    return copy.deepcopy(read(OUT / ('golden-' + kind + '-v03.json'))['fixture'])


def synthetic_plan(multiplier=1, unit='m'):
    p = new.complete_plan()
    p['multiplier']['value'] = multiplier
    p['unit_execution_contract']['multiplier'].update(original_value=str(multiplier), normalized_value=str(multiplier))
    if unit == 'mm':
        g = p['geometry_basis']; g.update(base_length='10000', source_unit='mm', engineering_unit='mm')
        g['conversion'].update(from_unit='mm', to_unit='mm', converted_length='10000')
        p['unit_conversion_contract'].update(source_unit='mm', target_unit='mm')
        p['unit_execution_contract']['raw_geometry_conversion'] = copy.deepcopy(g['conversion'])
        for i, record in enumerate([p['base_path']] + p['owned_adjustments']):
            value = ['10000', '200', '300'][i]; record.update(unit='mm'); record['value' if i == 0 else 'length'] = value
            term = p['unit_execution_contract']['components'][i]; term.update(original_unit='mm', original_value=value)
            term['conversion'].update(source_unit='mm', factor='0.001')
    p['provenance']['route'] = {'path': 'synthetic-route.json', 'sha256': 'd' * 64}
    p['source_evidence_hashes']['route'] = copy.deepcopy(p['provenance']['route'])
    return new.seal(p)


class BuilderCurrent(unittest.TestCase): pass
class SafetyCurrent(unittest.TestCase): pass
class MigrationCurrent(unittest.TestCase): pass


def same_assertion(module, cls, name, replacements):
    def run(self):
        with ExitStack() as stack:
            for key, value in replacements.items():
                if hasattr(module, key): stack.enter_context(patch.object(module, key, value))
            case = cls(name)
            case.setUp()
            try: getattr(case, name)()
            finally: case.tearDown()
    return run


builder = new.load('design-net-quantity/tests', 'test_builder.py')
for name in unittest.defaultTestLoader.getTestCaseNames(builder.BuilderTests):
    setattr(BuilderCurrent, name, same_assertion(builder, builder.BuilderTests, name,
        dict(plan=project_plan, synthetic=synthetic_plan)))

for path in sorted((ROOT / 'safety-hardening').glob('test_*.py')):
    module = new.load('safety-hardening', path.name)
    for cls in [c for c in vars(module).values() if isinstance(c, type) and issubclass(c, unittest.TestCase) and c.__module__ == module.__name__]:
        for name in unittest.defaultTestLoader.getTestCaseNames(cls):
            replacements = dict(plan=synthetic_plan, item=synthetic_item)
            # This assertion executes the exported plan: use the current exporter.
            # The separate historical-format assertion still exercises plan_v02.
            if name == 'test_no_correction_export_is_buildable_and_immutable':
                replacements['load'] = current_loader
            setattr(SafetyCurrent, 'test_' + path.stem + '_' + name, same_assertion(module, cls, name,
                replacements))

migration = new.load('contract-migration/tests', 'test_migration.py')
for cls in (migration.SourceBackedSafety, migration.SourceBackedBuilder, migration.SourceBackedGate, migration.SourceBackedEligibility):
    if hasattr(cls, 'setUpClass'): cls.setUpClass()
    for name in unittest.defaultTestLoader.getTestCaseNames(cls):
        setattr(MigrationCurrent, 'test_' + cls.__name__ + '_' + name,
            same_assertion(migration, cls, name, dict(plan=project_plan)))


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'contract-migration'))
    from run_suite import Recorded
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in (BuilderCurrent, SafetyCurrent, MigrationCurrent))
    result = unittest.TextTestRunner(verbosity=2, resultclass=Recorded).run(suite)
    with (OUT / sys.argv[1]).open('x', encoding='utf-8') as stream:
        json.dump(dict(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                       skipped=len(result.skipped), cases=result.cases), stream, ensure_ascii=False, indent=2)
    sys.exit(0 if result.wasSuccessful() else 1)
