import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'contract-migration'))
from migrate import OUT, ROOT, SNAPSHOT, ITEMS, BUNDLE, read, sha, digest, pointer, load, top_level_identity, complete_bound_identities, changes


def wrapper(name):return read('outputs/source-backed-contract-migration-20261008/fixtures/'+name+'.json')
def fixture(name):return copy.deepcopy(wrapper(name)['fixture'])
def plan(kind='conduit'):return fixture('golden-'+kind+'-plan-v2')
def item(kind='conduit'):return fixture('golden-'+kind+'-eligibility-v2')


def frozen(kind):
    path='outputs/golden-project-measurement-rules-20261004/design-net-quantities.json'
    q=read(path)['quantities'][0 if kind=='conduit' else 1]
    # Additive comparison view; no historical quantity fields are rewritten on disk.
    return dict(scope=copy.deepcopy(plan(kind)['binding']),quantity_kind=kind,approved_semantic_role='fire_alarm_bus_segment',
        specification=q['spec'],installation_method=q['installation'],computed_quantity=dict(reported_value=q['value'],unit=q['unit']),
        multiplier=q['countMultiplier'],source_id=q['id'],source_artifact=path,source_sha256=sha(ROOT/path))


class Migration(unittest.TestCase):
    def test_record_integrity_and_sources_for_every_added_field(self):
        for entry in read('outputs/source-backed-contract-migration-20261008/migration-manifest.json') + read('outputs/source-backed-contract-migration-20261008/supplemental-manifest.json'):
            w=read(entry['target_fixture'])
            self.assertEqual(w['record_hash'],digest({k:v for k,v in w.items() if k!='record_hash'}))
            self.assertEqual(w['fixture_hash'],digest(w['fixture']))
            for field in ('migration_id','source_fixture','target_fixture','old_schema_version','new_schema_version',
                          'added_fields','source_evidence_for_each_added_field','migration_reason','migrated_at','migration_tool'):
                self.assertIn(field,w)
            self.assertEqual(set(w['added_fields']),set(w['source_evidence_for_each_added_field']))
            for change in w['field_changes']:
                self.assertTrue(change['source_evidence'])
                for s in change['source_evidence']:
                    self.assertEqual(sha(ROOT/s['path']),s['sha256'])
                    if s['path'].endswith('.json'):pointer(read(s['path']),s.get('pointer',''))
                if change['path'].endswith('/parent_path'):
                    self.assertTrue(all(s.get('extraction_scope')=='ModelSpaceTopLevelAllLayers' for s in change['source_evidence']))
            self.assertFalse(w['historical_files_modified'])

    def test_all_migration_deltas_match_real_legacy_loader_input(self):
        original=load('quantity-eligibility','evidence.py').load_evidence(ROOT/ITEMS)['objects']
        bundle=load('project-evidence-gate','evidence.py').load_bundle(ROOT/BUNDLE)
        inputs={'golden-gate-v2':dict(candidate=original[0]['semantic_gate']['provenance']['candidate'],bundle=bundle,context=original[0]['semantic_gate']['provenance']['context'])}
        for i,k in enumerate(('conduit','wire')):
            inputs['golden-'+k+'-eligibility-v2']=original[i]
            inputs['golden-'+k+'-plan-v2']=read('outputs/quantity-build-plan-v02/golden-'+k+'-v02.json')
        for name,before in inputs.items():
            w=wrapper(name)
            recorded=[{k:v for k,v in c.items() if k not in ('source_evidence','evidence_type')} for c in w['field_changes']]
            self.assertEqual(changes(before,w['fixture']),recorded,name)
        for projection in read('outputs/source-backed-contract-migration-20261008/source-input-projections.json')['records'].values():
            for ref in projection['loaders']+projection['sources']:self.assertEqual(sha(ROOT/ref['path']),ref['sha256'])

    def test_no_assumed_top_level_when_snapshot_does_not_prove_it(self):
        project=plan()['binding']['project_id']
        self.assertRaises(ValueError,top_level_identity,SNAPSHOT,'NONEXISTENT',project,'edge')
        self.assertRaises(ValueError,top_level_identity,SNAPSHOT,'13CF5',project,'segment')

    def test_original_gate_blocked_migrated_gate_passes(self):
        m=load('project-evidence-gate');w=wrapper('golden-gate-v2');new=w['fixture']
        legacy=read(ITEMS)['objects'][0]['semantic_gate']['provenance']
        result=m.evaluate_semantics(legacy['candidate'],read(BUNDLE),legacy['context'])
        self.assertFalse(result['semantic_gate_passed']);self.assertEqual(result['project_specific_status'],'unresolved')
        result=m.evaluate_semantics(**new)
        self.assertTrue(result['semantic_gate_passed'])
        self.assertEqual(result['approved_semantic_role'],'fire_alarm_bus_segment')
        for e in result['accepted_evidence']:self.assertEqual(e['object_identity'],result['object_identity'])

    def test_each_original_eligibility_blocked_each_migrated_passes(self):
        evidence=load('quantity-eligibility','evidence.py').load_evidence(ROOT/ITEMS)
        m=load('quantity-eligibility')
        for i,k in enumerate(('conduit','wire')):
            with self.subTest(kind=k):
                old=m.resolve_eligibility(evidence['objects'][i]);self.assertFalse(old['design_net_quantity_generation_allowed'])
                self.assertTrue(any('identity' in r for r in old['blocking_reasons']))
                new=m.resolve_eligibility(item(k));self.assertEqual(new['quantity_eligibility_status'],'eligible',new['blocking_reasons'])

    def test_each_original_plan_blocked_each_migrated_replays_legacy(self):
        m=load('design-net-quantity','builder.py')
        for k in ('conduit','wire'):
            with self.subTest(kind=k):
                legacy=read('outputs/quantity-build-plan-v02/golden-'+k+'-v02.json')
                self.assertEqual(m.build(legacy,[])['status'],'contract_violation')
                result=m.replay_validate(plan(k),frozen(k))
                self.assertEqual(result['status'],'replay_value_matched_legacy_evidence_incomplete')
                self.assertTrue(result['numeric_match']);self.assertFalse(result['evidence_contract_match'])
                self.assertEqual(result['quantity']['computed_quantity']['exact_value'],'7.77128331912231535912969050917979628')
                self.assertEqual(plan(k)['multiplier']['value'],1)

    def test_native_replay_positive_and_full_review_changes(self):
        m=load('design-net-quantity','builder.py');p=plan()
        # In-memory native test object; no issuance, registry or frozen write.
        native=m.replay_validate(p,frozen('conduit'))['quantity']
        self.assertEqual(m.replay_validate(p,native)['status'],'replay_matched')
        for field in ('specification','geometry_basis','height_evidence','deduplication'):
            x=copy.deepcopy(p);x[field]['provenance']=copy.deepcopy(x[field]['provenance'])+[{'test_mutation':'different_review'}]
            m.seal(x);r=m.replay_validate(x,native)
            self.assertTrue(r['numeric_match']);self.assertFalse(r['evidence_contract_match'])
        for field in ('owner','assumption'):
            x=copy.deepcopy(p)
            if field=='owner':x['owned_adjustments'][0]['owner']['parent_path']=['foreign']
            else:x['assumptions'][0]['value']='different test assumption'
            self.assertNotEqual(m.replay_validate(m.seal(x),native)['status'],'replay_matched')

    def test_synthetic_inputs_not_promoted_without_sources(self):
        for n in ('synthetic-item','synthetic-plan','synthetic-gate'):
            w=wrapper('synthetic-gate-callable-retained' if n=='synthetic-gate' else n+'-legacy-incomplete');self.assertEqual(w['status'],'legacy_incomplete')
            self.assertTrue(w['missing_evidence']);self.assertEqual(w['added_fields'],[])
        x=fixture('synthetic-item-legacy-incomplete')
        self.assertFalse(load('quantity-eligibility').resolve_eligibility(x)['design_net_quantity_generation_allowed'])
        p=fixture('synthetic-plan-legacy-incomplete')
        self.assertEqual(load('design-net-quantity','builder.py').build(p,[])['status'],'contract_violation')

    def test_actual_gate_synthetic_callable_remains_legacy_rejected(self):
        old=load('project-evidence-gate','tests/test_resolver.py')
        result=old.run(records=[old.evidence()])
        self.assertFalse(result['semantic_gate_passed'])
        self.assertEqual(result['project_specific_status'],'unresolved')
        actual=fixture('synthetic-gate-callable-retained')
        self.assertFalse(load('project-evidence-gate').evaluate_semantics(**actual)['semantic_gate_passed'])
        with patch.object(old,'evaluate_semantics',lambda c,b,x:dict(candidate=c,bundle=b,context=x)):
            self.assertEqual(actual,old.run(records=[old.evidence()]))

    def test_no_height_upgrade_and_real_height_provenance(self):
        for k in ('conduit','wire'):
            old=read('outputs/quantity-build-plan-v02/golden-'+k+'-v02.json');p=plan(k)
            self.assertEqual(old['height_evidence']['status'],p['height_evidence']['status'])
            self.assertEqual(old['height_evidence']['provenance'],p['height_evidence']['provenance'])
            self.assertEqual(p['height_requirement'],'required')
            self.assertEqual(old['base_path']['value'],p['base_path']['value'])
            self.assertEqual(old['corrections_applied'],p['corrections_applied'])
        self.assertEqual(fixture('synthetic-item-legacy-incomplete')['height']['status'],'not_applicable')

    def test_new_gate_cannot_authorize_other_instance(self):
        x=fixture('golden-gate-v2');x['candidate']['parent_path']=['I2'];x['context']['parent_path']=['I2']
        self.assertFalse(load('project-evidence-gate').evaluate_semantics(**x)['semantic_gate_passed'])

    def test_full_source_backed_pipeline_export_and_replay(self):
        for k in ('conduit','wire'):
            x=item(k);d=load('quantity-eligibility').resolve_eligibility(x)
            p=load('quantity-eligibility','plan_v02.py').export_plan(d,digest(d),None,read('outputs/quantity-build-plan-v02/project-numeric-reporting-policy.json'))
            r=load('design-net-quantity','builder.py').replay_validate(p,frozen(k))
            self.assertTrue(r['numeric_match'])
            self.assertEqual(r['status'],'replay_value_matched_legacy_evidence_incomplete')

    def test_existing_json_and_python_frozen(self):
        b=read('outputs/source-backed-contract-migration-20261008/baseline.json')
        for group in ('json_hashes','existing_python_hashes'):
            for path,h in b[group].items():self.assertEqual(sha(ROOT/path),h,path)


# Re-execute the exact historical project Eligibility assertions with sourced v2 inputs.
# The historical class, expected values and original fixture are untouched.
old_eligibility=load('quantity-eligibility','tests/test_resolver.py')
class SourceBackedEligibility(old_eligibility.Eligibility):
    @classmethod
    def setUpClass(cls):cls.fixtures=[item('conduit'),item('wire')]

# Historical project-plan Builder assertions can also be rerun unchanged.
old_builder=load('design-net-quantity','tests/test_builder.py')
PROJECT_BUILDER_TESTS=['test_conduit_replay','test_wire_replay','test_schema','test_provenance','test_dedup',
    'test_blocked_edges','test_duplicate','test_decimal','test_correction','test_replay_mismatch','test_wrong_frozen_scope']
class SourceBackedBuilder(unittest.TestCase):pass
for name in PROJECT_BUILDER_TESTS:
    def run(self, name=name):
        case=old_builder.BuilderTests(name)
        with patch.object(old_builder,'plan',plan):getattr(case,name)()
    setattr(SourceBackedBuilder,name,run)

# The historical real-project Gate assertions also remain unchanged.
old_gate=load('project-evidence-gate','tests/test_resolver.py')
class SourceBackedGate(unittest.TestCase):
    def test_golden_and_four_unapproved_edges_original_assertions(self):
        implementation=load('project-evidence-gate').evaluate_semantics
        def sourced(c,b,context):
            identity,_=top_level_identity(SNAPSHOT,c['edge_handle'],b['project_id'],'edge')
            complete=copy.deepcopy(c);complete.update(identity)
            bound=copy.deepcopy(b);bound['drawing_ref']=identity['drawing_ref']
            complete_bound_identities(bound,plan()['binding'])
            return implementation(complete,bound,identity)
        with patch.object(old_gate,'evaluate_semantics',sourced):
            old_gate.Project('test_golden_and_four_unapproved_edges').test_golden_and_four_unapproved_edges()

    def test_v2_direct_conflict_pending_and_weak_are_not_admitted(self):
        m=load('project-evidence-gate')
        for kind in ('conflicting','pending','weak'):
            x=fixture('golden-gate-v2')
            if kind=='weak':x['bundle']['evidence'][0]['evidence_type']='manufacturer_generic'
            else:
                e=copy.deepcopy(x['bundle']['evidence'][0]);e['evidence_id']='adversarial-second-claim'
                if kind=='conflicting':e['semantic_role']='contradictory_role_for_negative_test'
                else:e['status']='unresolved'
                x['bundle']['evidence'].append(e);x['bundle']['bindings'][0]['evidence_ids'].append(e['evidence_id'])
            r=m.evaluate_semantics(**x)
            self.assertFalse(r['semantic_gate_passed'])
            self.assertEqual(r['project_specific_status'],'conflicting' if kind=='conflicting' else 'partial')

    def test_v2_candidate_is_overridden_by_original_project_evidence(self):
        x=fixture('golden-gate-v2');x['candidate']['candidate_role']='control_or_feedback'
        r=load('project-evidence-gate').evaluate_semantics(**x)
        self.assertTrue(r['semantic_gate_passed']);self.assertTrue(r['candidate_overridden'])
        self.assertEqual(r['approved_semantic_role'],'fire_alarm_bus_segment')

class SourceBackedSafety(unittest.TestCase):
    def test_metadata_and_native_frozen_tamper(self):
        m=load('design-net-quantity','builder.py');p=plan();q=m.replay_validate(p,frozen('conduit'))['quantity']
        p['binding']['audit_note']='test metadata';m.seal(p)
        self.assertEqual(m.build(p,[q])['status'],'duplicate_detected')
        q['evidence_contract']['records']['height_evidence']['status']='unknown'
        self.assertNotEqual(m.replay_validate(p,q)['status'],'replay_matched')

    def test_changed_correction_same_id_does_not_match(self):
        m=load('design-net-quantity','builder.py');p=plan();q=m.replay_validate(p,frozen('conduit'))['quantity']
        c=p['corrections_applied']['evidence'];c['basis']='adversarial review change';m.seal(c);m.seal(p)
        r=m.replay_validate(p,q);self.assertTrue(r['numeric_match']);self.assertFalse(r['evidence_contract_match'])

    def test_missing_geometry_and_height_cannot_use_top_eligible(self):
        m=load('design-net-quantity','builder.py')
        for field in ('geometry_basis','height_evidence'):
            p=plan();del p[field]
            self.assertEqual(m.build(m.seal(p),[])['status'],'contract_violation')

    def test_scope_and_ownership_cannot_migrate_to_other_instance(self):
        m=load('design-net-quantity','builder.py');p=plan()
        p['owned_adjustments'][0]['owner']['parent_path']=['I2']
        self.assertEqual(m.build(m.seal(p),[])['status'],'contract_violation')

if __name__=='__main__':unittest.main(verbosity=2)
