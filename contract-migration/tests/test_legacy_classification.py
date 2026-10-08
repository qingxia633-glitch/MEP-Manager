"""Each legacy mismatch has an executable fail-closed proof, not an ignored failure."""
import copy
import json
import unittest
from pathlib import Path
from test_migration import ROOT, read, sha, load, fixture
import test_migration as migration

CATALOG=read('contract-migration/classification-catalog.json')['entries']

class LegacyClassifications(unittest.TestCase):
    def verify_case(self,entry):
        src=entry['original_assertions'];self.assertEqual(sha(ROOT/src['path']),src['sha256'])
        raw=read('outputs/source-backed-contract-migration-20261008/regression/'+entry['suite']+'.json')
        case=next(c for c in raw['cases'] if c['test_id']==entry['test_id'])
        self.assertIn(case['raw_status'],('failure','error'))
        family=entry['input_family'];name=entry['test_id'].rsplit('.',1)[-1]
        if family=='golden_eligibility':
            old=load('quantity-eligibility','evidence.py').load_evidence(ROOT/'quantity-eligibility/fixtures/golden.json')['objects'][0]
            r=load('quantity-eligibility').resolve_eligibility(old)
            self.assertFalse(r['design_net_quantity_generation_allowed'])
            self.assertTrue(any('identity' in s for s in r['blocking_reasons']))
            migration.SourceBackedEligibility.setUpClass()
            getattr(migration.SourceBackedEligibility(name),name)()
        elif family=='golden_plan':
            p=read('outputs/quantity-build-plan-v02/golden-conduit-v02.json')
            r=load('design-net-quantity','builder.py').build(p,[])
            self.assertEqual(r['status'],'contract_violation')
            getattr(migration.SourceBackedBuilder(name),name)()
        elif family=='golden_gate':
            obj=read('quantity-eligibility/fixtures/golden.json')['objects'][0]
            g=obj['semantic_gate']['provenance'];r=load('project-evidence-gate').evaluate_semantics(g['candidate'],read('project-evidence-gate/project-evidence/garage-golden.json'),g['context'])
            self.assertFalse(r['semantic_gate_passed'])
            migration.SourceBackedGate('test_golden_and_four_unapproved_edges_original_assertions').test_golden_and_four_unapproved_edges_original_assertions()
        elif family=='synthetic_gate':
            old=fixture('synthetic-gate-callable-retained')
            self.assertFalse(load('project-evidence-gate').evaluate_semantics(**old)['semantic_gate_passed'])
        elif family=='synthetic_applicability':
            old=load('project-rule-applicability','tests/test_resolver.py')
            q=old.request();q['object_facts']=[old.witness()]
            bundle=old.to_gate_evidence(old.resolve(old.rule(),q))
            bundle['bindings'][0]['review_status']='reviewed';bundle['evidence'][0]['status']='supported'
            r=load('project-evidence-gate').evaluate_semantics({'edge_handle':'edge','candidate_role':'unknown'},bundle,old.CTX)
            self.assertFalse(r['semantic_gate_passed'])
            self.assertEqual(r['project_specific_status'],'unresolved')
        elif family=='synthetic_item':
            x=fixture('synthetic-item-legacy-incomplete')
            self.assertEqual(x['height']['status'],'not_applicable')
            self.assertFalse(load('quantity-eligibility').resolve_eligibility(x)['design_net_quantity_generation_allowed'])
        elif family=='synthetic_plan':
            p=fixture('synthetic-plan-legacy-incomplete')
            self.assertNotIn('height_evidence',p)
            self.assertEqual(load('design-net-quantity','builder.py').build(p,[])['status'],'contract_violation')
        else:self.fail('Unclassified input family')

for index,entry in enumerate(CATALOG):
    def test(self,entry=entry):self.verify_case(entry)
    setattr(LegacyClassifications,'test_'+str(index).zfill(2)+'_'+entry['test_id'].split('.')[-1],test)

class ClassificationCoverage(unittest.TestCase):
    def test_no_unclassified_historical_failures(self):
        actual=set()
        for suite in ('geometry-connection','device-role','candidate-semantic','project-rule-applicability','project-evidence-gate','quantity-eligibility','design-net-quantity','project-evidence-discovery','safety-hardening'):
            raw=read('outputs/source-backed-contract-migration-20261008/regression/'+suite+'.json')
            actual.update((suite,c['test_id']) for c in raw['cases'] if c['raw_status']!='passed')
        self.assertEqual(actual,{(e['suite'],e['test_id']) for e in CATALOG})

if __name__=='__main__':unittest.main(verbosity=2)
