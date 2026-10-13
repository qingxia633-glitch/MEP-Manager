"""Synthetic runner tests; never counted as real benchmark cases."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prediction
import scoring
import run_shadow_benchmark as runner


def case(kind='true_supported', boundary=False):
    c = {'case_id': 'SYNTH-1', 'project_id': 'P', 'drawing': 'D.dwg',
         'report_sha256': 'a'*64, 'manifest_version': '2',
         'acquisition_scope': {'mode': 'ModelSpaceTopLevelAllLayers',
             'model_space_top_level': 'included', 'nested_blocks': 'not expanded',
             'xref_contents': 'not expanded', 'layouts': 'not included'},
         'target_identity': {'project_id': 'P', 'drawing': 'D.dwg',
             'snapshot_id': 'a'*64, 'handle': 'I', 'parent_path': [],
             'entity_type': 'INSERT', 'child': {'handle': 'T', 'parent_path': ['I'], 'entity_type': 'ATTRIB'}},
         'adjudication_class': kind, 'evidence_type': 'direct_object_binding'}
    if boundary:
        c.update(benchmark_dimension='object_ownership_and_discovery_semantic_boundary',
                 object_binding_adjudication=kind, semantic_boundary_adjudication='preserved')
    return c


def machine(binding=True):
    b = {'project_id': 'P', 'source_drawing': 'D.dwg', 'target_id': 'I',
         'target_parent_path': [], 'target_type': 'device', 'annotation_handle': 'T',
         'annotation_parent_path': ['I'], 'binding_method': 'direct_object_binding',
         'binding_status': 'supported', 'relation': 'text_attached_to_object', 'line_codes': ['S']}
    return {'object_type': 'ProjectEvidenceDiscoveryResult', 'version': '0.1',
            'source_drawing': 'D.dwg', 'report_integrity': 'verified',
            'shadow_evaluable': True, 'acquisition_scope_status': 'eligible',
            'bindings': [b] if binding else [], 'evidence': [],
            'propagation_roots': [], 'membership_candidates': [], 'edge_summaries': {}}


class RunnerTests(unittest.TestCase):
    def valid_input(self, td, **changes):
        p=Path(td)/'report.txt';mp=Path(td)/'manifest.json'
        fields={'DWG':'D.dwg','ExtractorVersion':'2.4-leader-evidence-v1',
            'AcquisitionMode':'ModelSpaceTopLevelAllLayers','ModelSpaceTopLevel':'included',
            'NestedBlocks':'not expanded','AllLayers':'included; including off/frozen',
            'XrefContents':'not expanded','PaperSpaceLayouts':'not included'}
        fields.update(changes)
        p.write_text('\n'.join(k+'="'+v+'"' for k,v in fields.items())+'\nReadErrorCount=0\nEND_OF_REPORT: scan finished. Inspect errors and scope limitations before interpreting results.\n',encoding='utf-8-sig')
        from report_manifest import write_manifest
        write_manifest(p,mp)
        c=case();c['report_sha256']=prediction.sha256(p);c['target_identity']['snapshot_id']=c['report_sha256']
        return c,runner.prediction_request(c,{'report_path':str(p),'manifest_path':str(mp)})

    def test_verified_input_passes_only_explicit_discovery_arguments(self):
        with tempfile.TemporaryDirectory() as td:
            c,r=self.valid_input(td);seen=[]
            def fake(*args,**kw):seen.append((args,kw));return machine()
            self.assertEqual(prediction.predict(r,fake)['case_status'],'executed')
            self.assertEqual(set(seen[0][1]),{'manifest','project_id','encoding','xy_tolerance','nearby_distance'})

    def test_wrong_drawing_exporter_and_scope(self):
        for changes in [{'DWG':'other.dwg'},{'ExtractorVersion':'2.3'},{'AllLayers':'partial'}, {'PaperSpaceLayouts':'included'}]:
            with self.subTest(changes=changes),tempfile.TemporaryDirectory() as td:
                c,r=self.valid_input(td,**changes);calls=[]
                self.assertEqual(prediction.predict(r,lambda *a,**k:calls.append(1))['case_status'],'input_integrity_failure')
                self.assertEqual(calls,[])

    def test_project_identity_missing(self):
        r=runner.prediction_request(case(),{'report_path':'x','manifest_path':'y'});r['project_id']=''
        with self.assertRaises(ValueError):prediction.validate_request(r)

    def test_ledger_labels_do_not_change_prediction_request(self):
        c=case();paths={'report_path':'x','manifest_path':'y'};before=runner.prediction_request(c,paths)
        c.update(adjudication_class='false_supported',pass_fail='FAIL',notes={'answer':'private'},blind_result={'status':'magic'})
        self.assertEqual(before,runner.prediction_request(c,paths))

    def test_all_predictions_frozen_before_scoring(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);c=case();other=copy.deepcopy(c);other['case_id']='SYNTH-2'
            ledger=td/'ledger.json';ledger.write_text(json.dumps({'version':'0.2','cases':[c,other]}))
            im=td/'map.json';im.write_text(json.dumps({'cases':[{'case_id':x['case_id'],'report_path':'missing','manifest_path':'missing'} for x in [c,other]]}))
            events=[];original=scoring.score_file
            def worker(argv,**kw):
                request=json.loads(Path(argv[argv.index('--request')+1]).read_text());prediction.validate_request(request)
                prediction.freeze(argv[argv.index('--output')+1],{'case_id':request['case_id'],'target_identity':request['target_identity'],'input_report_sha256':request['report_sha256'],'case_status':'executed','fresh_machine_result':machine()})
                events.append('prediction');return type('Process',(),{'returncode':0})()
            def score(*args):
                self.assertEqual(events.count('prediction'),2);self.assertTrue((td/'out/prediction-index.json').exists());events.append('score');return original(*args)
            with patch.object(runner.subprocess,'run',worker),patch.object(scoring,'score_file',score):
                result=runner.run(ledger,im,td/'out')
            self.assertEqual(events,['prediction','prediction','score','score']);self.assertEqual(result['summary']['passed'],2)

    def test_semantic_approval_in_related_edge_summary(self):
        m=machine();m['evidence']=[{'source_handle':'T','evidence_id':'A'}];m['edge_summaries']={'E':{'nearby_evidence_ids':['A'],'approved_semantic_role':'bus'}}
        self.assertIn('semantic_overreach',self.score(case(boundary=True),m)['failure_class'])

    def test_unknown_machine_contract(self):
        m=machine();m['version']='future'
        self.assertIn('execution_error',self.score(case(),m)['failure_class'])

    def test_malformed_machine_payload(self):
        for m in [None, {'bindings':'not a list'}, dict(machine(),bindings=['not a record'])]:
            with self.subTest(machine=m):
                self.assertIn('execution_error',self.score(case(),m)['failure_class'])

    def score(self, c, m):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'prediction.json'
            prediction.freeze(p, {'case_id': c['case_id'], 'case_status':'executed',
                'target_identity': c['target_identity'], 'input_report_sha256':c['report_sha256'],
                'fresh_machine_result':m})
            before=p.read_bytes()
            result=scoring.score_file(p, hashlib.sha256(before).hexdigest(), c)
            self.assertEqual(before,p.read_bytes())
            return result

    def test_supported_pass(self):
        self.assertEqual(self.score(case(),machine())['pass_fail'],'PASS')

    def test_unresolved_pass(self):
        self.assertEqual(self.score(case('true_unresolved'),machine(False))['pass_fail'],'PASS')

    def test_false_negative(self):
        self.assertIn('false_negative',self.score(case(),machine(False))['failure_class'])

    def test_false_positive(self):
        self.assertIn('false_positive',self.score(case('true_unresolved'),machine())['failure_class'])

    def test_wrong_binding(self):
        m=machine();m['bindings'][0]['target_id']='OTHER'
        self.assertIn('wrong_binding',self.score(case(),m)['failure_class'])

    def test_foreign_parent_or_project(self):
        for key,value in [('target_parent_path',['FOREIGN']),('project_id','FOREIGN')]:
            m=machine();m['bindings'][0][key]=value
            self.assertIn('wrong_binding',self.score(case(),m)['failure_class'])

    def test_conflict(self):
        m=machine();m['bindings'][0]['binding_status']='conflicting'
        self.assertIn('conflict_mismatch',self.score(case(),m)['failure_class'])

    def test_boundary_lexical_only_pass(self):
        self.assertEqual(self.score(case(boundary=True),machine())['pass_fail'],'PASS')

    def test_boundary_extra_line_binding(self):
        m=machine();extra=copy.deepcopy(m['bindings'][0]);extra.update(target_id='E',target_type='edge');m['bindings'].append(extra)
        self.assertIn('semantic_overreach',self.score(case(boundary=True),m)['failure_class'])

    def test_boundary_explicit_approval(self):
        m=machine();m['approved_semantic_role']='alarm_bus'
        self.assertIn('semantic_overreach',self.score(case(boundary=True),m)['failure_class'])

    def test_nearby_not_binding(self):
        m=machine();m['evidence']=[{'source_handle':'T','parent_path':['I'],
            'target_candidates':[{'target_id':'E','relation':'text_near_edge'}], 'line_codes':['S']}]
        self.assertEqual(self.score(case(boundary=True),m)['pass_fail'],'PASS')

    def test_prediction_cannot_receive_labels(self):
        request=runner.prediction_request(case(),{'report_path':'x','manifest_path':'y'})
        self.assertNotIn('adjudication_class',json.dumps(request))
        request['pass_fail']='PASS'
        with self.assertRaises(ValueError):prediction.validate_request(request)

    def test_nested_label_rejected(self):
        request=runner.prediction_request(case(),{'report_path':'x','manifest_path':'y'})
        request['target_identity']['expected']='supported'
        with self.assertRaises(ValueError):prediction.validate_request(request)

    def test_duplicate_case_rejected(self):
        with self.assertRaises(ValueError):runner.validate_inputs({'version':'0.2','cases':[case(),case()]},{'cases':[]})

    def test_unknown_adjudication(self):
        with self.assertRaises(ValueError):scoring.expectation(case('magic'))

    def test_scoring_tampered_prediction(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'p.json';prediction.freeze(p,{'x':1})
            with self.assertRaises(ValueError):scoring.score_file(p,'0'*64,case())

    def test_freeze_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'p.json';prediction.freeze(p,{'x':1})
            with self.assertRaises(FileExistsError):prediction.freeze(p,{'x':2})

    def test_missing_input_skip(self):
        req=runner.prediction_request(case(),{'report_path':'not-present','manifest_path':'not-present'})
        called=[]
        result=prediction.predict(req,discover_fn=lambda *a,**k:called.append(True))
        self.assertEqual(result['case_status'],'input_unavailable');self.assertEqual(called,[])

    def test_hash_mismatch_no_execution(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'r.txt';p.write_text('bad');m=Path(td)/'m.json';m.write_text('{}')
            req=runner.prediction_request(case(),{'report_path':str(p),'manifest_path':str(m)})
            called=[];r=prediction.predict(req,discover_fn=lambda *a,**k:called.append(True))
            self.assertEqual(r['case_status'],'input_integrity_failure');self.assertEqual(called,[])

    def test_error_not_false_negative(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'p.json';prediction.freeze(p,{'case_id':'SYNTH-1','case_status':'input_unavailable','target_identity':case()['target_identity'],'input_report_sha256':None})
            r=scoring.score_file(p,prediction.sha256(p),case())
            self.assertEqual(r['pass_fail'],'SKIP');self.assertNotIn('false_negative',r['failure_class'])


if __name__=='__main__':unittest.main()
