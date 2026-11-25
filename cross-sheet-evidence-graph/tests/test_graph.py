"""Synthetic graph contracts; never real BX coverage."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'cross-sheet-evidence-graph'),str(ROOT/'explicit-cross-sheet-reference/tests')]
from test_references_v2 import fixture
from references_v2 import scan
from graph import build_graph

def sample(**kwargs):
    registry,context=fixture(**kwargs)
    return scan(registry,[context])

def build(d):return build_graph(d,'a'*64)

class GraphTests(unittest.TestCase):
    def test_candidate_preserved(self):
        d=sample();g=build(d)
        self.assertEqual(g['summary']['candidate'],1)
        self.assertEqual(g['records'][0]['source_reference'],d['source_references'][0])
        self.assertEqual(g['records'][0]['resolution'],d['resolutions'][0])
        self.assertFalse(g['formal_authorization'])

    def test_missing_identifier(self):
        g=build(sample(text='详见上级配电箱'))
        self.assertEqual(g['summary']['identifier_missing'],1)
        self.assertEqual(g['summary']['registry_exact_match_failed'],0)
        self.assertFalse(any(n['kind']=='source_identifier' for n in g['nodes']))

    def test_exact_miss(self):
        g=build(sample(count=0))
        self.assertEqual(g['summary']['identifier_missing'],0)
        self.assertEqual(g['summary']['registry_exact_match_failed'],1)

    def test_ambiguous_all_candidates(self):
        g=build(sample(count=2));self.assertEqual(g['summary']['ambiguous'],1)
        self.assertEqual(sum(e['relation']=='reported_target_candidate' for e in g['edges']),2)

    def test_drawing_layout_separate(self):
        g=build(sample(drawing_alias=True))
        kinds={n['kind'] for n in g['nodes']}
        self.assertTrue({'drawing_instance','layout_instance'}<=kinds)
        self.assertNotIn('sheet',kinds)
        self.assertEqual(g['summary']['ambiguous'],1)

    def test_conflict_preserved(self):
        d=sample();d['source_references'][0]['reference_extraction_status']='conflicting'
        d['resolutions'][0]['resolution_status']='conflicting'
        d['resolutions'][0]['resolution_reasons']=['source_or_target_identity_conflict']
        d['source_conflict_evidence']=[{'raw':'synthetic conflict'}]
        g=build(d);self.assertEqual(g['summary']['conflicting'],1)
        self.assertEqual(g['source_conflict_evidence'],d['source_conflict_evidence'])

    def test_stable_reference_node_across_targets(self):
        a=build(sample());b=build(sample(count=2))
        self.assertEqual(a['records'][0]['reference_node_id'],b['records'][0]['reference_node_id'])

    def test_empty_graph(self):self.assertEqual(build(sample(text='S'))['summary']['reference_count'],0)
    def test_no_mutation(self):
        d=sample();before=copy.deepcopy(d);build(d);self.assertEqual(d,before)
    def test_deterministic(self):self.assertEqual(build(sample()),build(sample()))
    def test_exact_duplicate(self):
        d=sample();d['source_references']*=2;d['resolutions']*=2
        self.assertEqual(build(d)['summary']['reference_count'],1)

    def rejected(self,mutate):
        d=sample();mutate(d)
        with self.assertRaises(ValueError):build(d)
    def test_v1(self):self.rejected(lambda d:d.update(version=1))
    def test_bool_version(self):self.rejected(lambda d:d.update(version=True))
    def test_registry_v1(self):self.rejected(lambda d:d.update(registry_version=1))
    def test_missing_resolution(self):self.rejected(lambda d:d.update(resolutions=[]))
    def test_orphan_resolution(self):self.rejected(lambda d:d['resolutions'][0].update(reference_id='foreign'))
    def test_missing_parent_path(self):self.rejected(lambda d:d['source_references'][0]['source_carrier_identity'].pop('parent_path'))
    def test_foreign_carrier(self):self.rejected(lambda d:d['source_references'][0]['source_carrier_identity'].update(project_id='other'))
    def test_foreign_target(self):self.rejected(lambda d:d['resolutions'][0]['target_candidates'][0].update(project_id='other'))
    def test_missing_provenance(self):self.rejected(lambda d:d['source_references'][0].update(provenance=[]))
    def test_source_provenance_mismatch(self):self.rejected(lambda d:d['resolutions'][0]['provenance'].update(source=[]))
    def test_sheet_fabrication(self):self.rejected(lambda d:d['resolutions'][0]['target_candidates'][0].update(target_kind='sheet'))
    def test_flattened_layout(self):self.rejected(lambda d:d['resolutions'][0]['target_candidates'][0].update(layout_instance_id=None))
    def test_false_supported(self):self.rejected(lambda d:d['resolutions'][0].update(resolution_status='supported'))
    def test_bad_status(self):self.rejected(lambda d:d['resolutions'][0].update(resolution_status='approved'))
    def test_contradictory_duplicate(self):
        def mutate(d):
            x=copy.deepcopy(d['source_references'][0]);x['raw_reference_text']='different';d['source_references'].append(x)
        self.rejected(mutate)
    def test_duplicate_target(self):self.rejected(lambda d:d['resolutions'][0]['target_candidates'].extend(copy.deepcopy(d['resolutions'][0]['target_candidates'])))
    def test_query_mismatch(self):self.rejected(lambda d:d['resolutions'][0].update(lookup_query='other'))
    def test_fake_zero_match(self):self.rejected(lambda d:d['resolutions'][0].update(lookup_status='not_found',resolution_status='unresolved'))
    def test_invalid_pin(self):
        with self.assertRaises(ValueError):build_graph(sample(),'invalid')

    def test_nested_carrier_identity_preserved(self):
        d=sample();d['source_references'][0]['source_carrier_identity']['parent_path']=['I1','I2']
        g=build(d)
        self.assertEqual(g['records'][0]['source_reference']['source_carrier_identity']['parent_path'],['I1','I2'])

    def test_candidate_alias_provenance_preserved(self):
        d=sample();g=build(d)
        edge=next(e for e in g['edges'] if e['relation']=='reported_target_candidate')
        self.assertEqual(edge['evidence'],d['resolutions'][0]['target_candidates'][0])

    def test_input_summary_not_trusted(self):
        d=sample();d['summary']['supported']=999
        self.assertEqual(build(d)['summary']['supported'],0)

    def test_result_does_not_alias_input(self):
        d=sample();g=build(d);g['records'][0]['source_reference']['raw_reference_text']='changed'
        self.assertNotEqual(d['source_references'][0]['raw_reference_text'],'changed')

    def test_missing_conflict_evidence_not_defaulted(self):
        self.rejected(lambda d:d.pop('source_conflict_evidence'))

    def cli(self,raw=None,pin=None,existing=False):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.json';out=Path(tmp)/'graph.json'
            p.write_bytes(raw if raw is not None else json.dumps(sample(),ensure_ascii=False).encode('utf-8'))
            before=p.read_bytes()
            if existing:out.write_text('protected')
            c=subprocess.run([sys.executable,'-B',str(ROOT/'cross-sheet-evidence-graph/resolve.py'),
                '--input',str(p),'--sha256',pin or hashlib.sha256(before).hexdigest(),'--output',str(out)],capture_output=True)
            self.assertEqual(p.read_bytes(),before)
            return c.returncode,out.read_text(encoding='utf-8') if out.exists() else None
    def test_cli_valid(self):
        code,value=self.cli();self.assertEqual(code,0);self.assertEqual(json.loads(value)['CrossSheetEvidenceGraphVersion'],1)
    def test_cli_hash_failure(self):
        code,value=self.cli(pin='0'*64);self.assertNotEqual(code,0);self.assertIsNone(value)
    def test_cli_overwrite_refused(self):
        code,value=self.cli(existing=True);self.assertNotEqual(code,0);self.assertEqual(value,'protected')
    def test_cli_duplicate_key(self):
        code,value=self.cli(raw=b'{"version":2,"version":2}');self.assertNotEqual(code,0);self.assertIsNone(value)
    def test_cli_nan(self):
        code,value=self.cli(raw=b'{"version":NaN}');self.assertNotEqual(code,0);self.assertIsNone(value)

if __name__=='__main__':unittest.main()
