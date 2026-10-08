"""Explicit Pass 2 adapters; originals and their raw outcomes remain untouched."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/post-hardening-pass2-20261008'
sys.path.insert(0, str(ROOT / 'post-hardening-pass2/tests'))
import test_pass2 as new
sys.path.insert(0, str(ROOT / 'contract-migration/tests'))
import test_migration as migration
previous = new.load('post-hardening-tests', 'test_findings.py')
boundaries = new.load('post-hardening-tests', 'test_contract_boundaries.py')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


class CurrentContract(unittest.TestCase):
    def scoped_legacy_assertion(self, module, cls, method):
        original_load = module.load

        def scoped_load(folder, filename='resolver.py'):
            implementation = original_load(folder, filename)
            if folder == 'project-evidence-discovery':
                annotations = sys.modules['annotations']
                original_report = annotations.load_report

                def declared_synthetic_report(path, *args, **kwargs):
                    # A NEW explicitly top-level synthetic fixture, never a project migration.
                    raw = Path(path).read_text(encoding='utf-8')
                    with tempfile.TemporaryDirectory() as directory:
                        target = Path(directory) / 'declared-synthetic-top-level.txt'
                        target.write_text(new.TOP_LEVEL + raw, encoding='utf-8')
                        return original_report(target, *args, **kwargs)
                annotations.load_report = declared_synthetic_report
            return implementation

        with patch.object(module, 'load', scoped_load):
            getattr(cls(method), method)()

    def test_original_owner_assertion_on_new_scoped_synthetic_input(self):
        self.scoped_legacy_assertion(previous, previous.Findings, 'test_P2_1_report_attribute_owner_binding')

    def test_original_duplicate_assertion_on_new_scoped_synthetic_input(self):
        self.scoped_legacy_assertion(boundaries, boundaries.Boundaries,
                                    'test_adapter_repeated_attribute_handle_keeps_owners_separate')

    def test_current_frozen_boundary(self):
        baseline = read(OUT / 'baseline.json')
        for group in ('json_hashes', 'historical_test_hashes'):
            for name, expected in baseline[group].items():
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)
        extra = read(OUT / 'supplemental-frozen-inventory.json')
        self.assertEqual(hashlib.sha256((ROOT / extra['source_inventory']).read_bytes()).hexdigest(), extra['source_inventory_sha256'])
        for name, expected in extra['json_hashes'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)

    def test_all_raw_mismatches_explicitly_accounted_for(self):
        original = read(ROOT / 'contract-migration/classification-catalog.json')['entries']
        expected = {(e['suite'], e['test_id']) for e in original}
        expected.update({
            ('post-hardening-tests', 'test_findings.Findings.test_P2_1_report_attribute_owner_binding'),
            ('post-hardening-tests', 'test_contract_boundaries.Boundaries.test_adapter_repeated_attribute_handle_keeps_owners_separate'),
            ('contract-migration', 'test_migration.Migration.test_existing_json_and_python_frozen')})
        actual = set()
        for name in {name for name, _ in expected} | {'geometry-connection', 'device-role', 'candidate-semantic', 'project-evidence-discovery'}:
            result = read(OUT / 'regression' / (name + '.json'))
            actual.update((name, c['test_id']) for c in result['cases'] if c['raw_status'] != 'passed')
        self.assertEqual(actual, expected, 'Unexpected failure must block completion')

    def test_private_golden_both_quantities_unchanged_replay(self):
        module = new.load('design-net-quantity', 'builder.py')
        for kind in ('conduit', 'wire'):
            p = migration.plan(kind)
            r = module.replay_validate(p, migration.frozen(kind))
            self.assertEqual(r['status'], 'replay_value_matched_legacy_evidence_incomplete')
            self.assertEqual(r['quantity']['computed_quantity']['exact_value'],
                             '7.77128331912231535912969050917979628')
            self.assertEqual(p['multiplier']['value'], 1)
            self.assertEqual(module.replay_validate(p, r['quantity'])['status'], 'replay_matched')

    def test_actual_report_load_discover_owner_identity(self):
        module = new.load('project-evidence-discovery', 'discovery.py')
        from annotations import load_report
        snapshot = ROOT / 'local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'
        project = read(ROOT / 'project-evidence-gate/project-evidence/garage-golden.json')['project_id']
        context = load_report(snapshot, project_id=project)
        result = module.discover(context)
        attributes = [a for a in context['annotations'] if a['type'] == 'ATTRIB']
        self.assertEqual(len(attributes), 2129)
        for a in attributes:
            self.assertEqual(a['attribute_handle'], a['handle'])
            self.assertEqual(a['owner_insert_handle'], a['parent_handle'])
            self.assertEqual(a['owner_parent_path'], [])
            self.assertEqual(a['attribute_parent_path'], [a['owner_insert_handle']])
            self.assertEqual(a['owner_insert_identity']['drawing_ref'], context['drawing_ref'])
        # Actual role/spec texts need not create semantic bindings. Do not invent any.
        self.assertFalse(context['unresolved_attributes'])
        self.assertIsInstance(result['bindings'], list)


if __name__ == '__main__':
    from run_suite import Recorded
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CurrentContract)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Recorded).run(suite)
    with (OUT / sys.argv[1]).open('x', encoding='utf-8') as stream:
        json.dump(dict(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                       skipped=len(result.skipped), cases=result.cases), stream, ensure_ascii=False, indent=2)
    sys.exit(0 if result.wasSuccessful() else 1)
