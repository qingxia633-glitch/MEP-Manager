"""New current-contract fixtures; old tests and old inputs remain unchanged."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/post-hardening-pass3-20261008'
sys.path.insert(0, str(ROOT / 'post-hardening-pass3/tests'))
import test_admission as new
old = new.load('post-hardening-pass2/tests', 'test_pass2.py')
ORIGINAL_LOAD = new.load


def synthetic_item():
    item = new.item()
    item['height_requirement'] = 'required'
    item['semantic_gate'] = copy.deepcopy(new.complete_plan()['semantic_gate'])
    return item


def current_loader(folder, filename='resolver.py'):
    return ORIGINAL_LOAD(folder, 'plan_v03.py' if folder == 'quantity-eligibility' and filename == 'plan_v02.py' else filename)


class Pass2Current(unittest.TestCase):
    """The same 24 assertions run on explicitly declared current synthetic inputs."""


def adapted(method):
    def test(self):
        with patch.object(old, 'plan', new.complete_plan), patch.object(old, 'item', synthetic_item), patch.object(old, 'load', current_loader):
            getattr(old.Pass2(method), method)()
    return test


for name in unittest.defaultTestLoader.getTestCaseNames(old.Pass2):
    setattr(Pass2Current, name, adapted(name))


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


class Current(unittest.TestCase):
    def test_real_source_backed_export_pipeline(self):
        migration = new.load('contract-migration/tests', 'test_migration.py')
        for kind in ('conduit', 'wire'):
            item = read(OUT / ('golden-' + kind + '-eligibility-v3.json'))['fixture']
            decision = new.load('quantity-eligibility').resolve_eligibility(item)
            self.assertEqual(decision['quantity_eligibility_status'], 'eligible', decision['blocking_reasons'])
            exporter = new.load('quantity-eligibility', 'plan_v03.py')
            policy = read(ROOT / 'outputs/quantity-build-plan-v02/project-numeric-reporting-policy.json')
            decision_hash = hashlib.sha256(json.dumps(decision, ensure_ascii=False, sort_keys=True,
                separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
            plan = exporter.export_plan(decision, decision_hash, None, policy)
            result = new.load('design-net-quantity', 'builder.py').replay_validate(plan, migration.frozen(kind))
            self.assertTrue(result['numeric_match'], result)
            self.assertEqual(result['status'], 'replay_value_matched_legacy_evidence_incomplete')

    def test_legacy_v02_is_blocked(self):
        result = new.load('design-net-quantity', 'builder.py').build(new.legacy_plan(), [])
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('legacy_incomplete', result['blocking_reasons'][0])

    def test_real_golden_both_v03_replay(self):
        migration = new.load('contract-migration/tests', 'test_migration.py')
        m = new.load('design-net-quantity', 'builder.py')
        for kind in ('conduit', 'wire'):
            plan = read(OUT / ('golden-' + kind + '-v03.json'))['fixture']
            r = m.replay_validate(plan, migration.frozen(kind))
            self.assertEqual(r['status'], 'replay_value_matched_legacy_evidence_incomplete', r)
            self.assertEqual(r['quantity']['computed_quantity']['exact_value'], '7.77128331912231535912969050917979628')
            self.assertEqual(r['quantity']['computed_quantity']['reported_value'], '7.771283319')
            self.assertEqual(plan['multiplier']['value'], 1)
            self.assertEqual(m.replay_validate(plan, r['quantity'])['status'], 'replay_matched')

    def test_private_migration_every_delta_has_source(self):
        def pointer(doc, path):
            for key in path.strip('/').split('/') if path else []:
                doc = doc[int(key)] if isinstance(doc, list) else doc[key]
            return doc
        for name in ('golden-conduit-v03.json', 'golden-wire-v03.json',
                     'golden-conduit-eligibility-v3.json', 'golden-wire-eligibility-v3.json'):
            wrapper = read(OUT / name)
            self.assertFalse(wrapper['historical_files_modified'])
            self.assertEqual(set(wrapper['added_fields']), set(wrapper['source_evidence_for_each_added_field']))
            for change in wrapper['field_changes']:
                self.assertTrue(change['source_evidence'])
                self.assertEqual(pointer(wrapper['fixture'], change['path']), change['value'])
                for ref in change['source_evidence']:
                    path = ROOT / ref['path']
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), ref['sha256'])
                    pointer(read(path), ref['pointer'])

    def test_actual_report(self):
        previous = new.load('post-hardening-pass2', 'current_contract_checks.py')
        previous.CurrentContract('test_actual_report_load_discover_owner_identity').test_actual_report_load_discover_owner_identity()

    def test_frozen_inventory(self):
        baseline = read(OUT / 'baseline.json')
        for group in ('json_hashes', 'historical_test_hashes'):
            for name, expected in baseline[group].items():
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'contract-migration'))
    from run_suite import Recorded
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2, resultclass=Recorded).run(suite)
    with (OUT / sys.argv[1]).open('x', encoding='utf-8') as stream:
        json.dump(dict(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                       skipped=len(result.skipped), cases=result.cases), stream, ensure_ascii=False, indent=2)
    sys.exit(0 if result.wasSuccessful() else 1)
