import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from annotations import load_report
from discovery import discover
from report_manifest import write_manifest
from report_text import serialized_field,decode_exported_string
from test_leader_v1 import HEADER, BODY

class LeaderHardening(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.path=Path(self.tmp.name)/'report.txt'
 def context(self,header=HEADER,body=BODY,**kw):
  self.path.write_text(header+body,encoding=kw.get('encoding','utf-8'))
  return load_report(self.path,'synthetic-project',**kw)
 def rejected(self,c,condition):
  result=discover(c)
  self.assertFalse(result['bindings'])
  leader=result['leader_diagnostics'][0]
  self.assertFalse(leader['validation'][condition])
  self.assertEqual(leader['association_status'],'unresolved')
  return result
 def test_M1_legacy_scope_unknown(self):
  c=self.context(HEADER.replace('ModelSpaceTopLevel="included"','ModelSpaceTopLevel="unknown"'),BODY.replace('LeaderEvidenceVersion="1"\n',''))
  self.rejected(c,'scope');self.assertIsNone(c['leaders'][0]['parent_path'])
 def test_M2_direct_unknown_version(self):
  c=self.context();c['leaders'][0].update(evidence_version='999',association_status='explicit')
  self.rejected(c,'version')
 def test_M2_direct_false_validation(self):
  c=self.context();c['leaders'][0]['validation']['geometry']=False
  c['leaders'][0]['association_status']='explicit';self.rejected(c,'declared_validation')
 def test_M2_direct_non_arrow_end(self):
  c=self.context();c['leaders'][0]['arrow_wcs']=[5,5,0]
  c['targets'][0]['geometry']['vertices_wcs']=[[0,5,0],[10,5,0]]
  self.rejected(c,'arrow_origin')
 def test_L1_dimension(self):
  self.rejected(self.context(HEADER.replace('DXF_Type="MTEXT"','DXF_Type="DIMENSION"'),BODY.replace('AnnotationType="MTEXT"','AnnotationType="DIMENSION"')),'annotation_type')
 def test_L1_type_mismatch(self):
  self.rejected(self.context(body=BODY.replace('AnnotationType="MTEXT"','AnnotationType="TEXT"')),'annotation_type')
 def test_nan(self):
  self.rejected(self.context(body=BODY.replace('LeaderVertex_WCS=(5 5 0)','LeaderVertex_WCS=(NaN 5 0)')),'geometry')
 def test_ocs(self):
  self.rejected(self.context(body=BODY.replace('LeaderCoordinateSystem="WCS"','LeaderCoordinateSystem="OCS"')),'coordinates')
 def test_missing_annotation(self):
  self.rejected(self.context(body=BODY.replace('AnnotationHandle="A1"','AnnotationHandle="FFFF"')),'annotation_exists')
 def test_ambiguous_intersection(self):
  c=self.context();c['targets'].append({'id':'E2','target_type':'edge','geometry':{'type':'LINE','vertices_wcs':[[5,-5,0],[5,5,0]],'complete':True}})
  r=discover(c);self.assertEqual(len(r['bindings']),2)
  self.assertEqual([x['binding_status'] for x in r['bindings']],['partial','partial'])
  self.assertEqual(r['evidence'][0]['binding_status'],'partial')
  self.assertEqual(r['leader_diagnostics'][0]['target_match_count'],2)
 def test_no_snap_diagnostic(self):
  c=self.context();c['targets'][0]['geometry']['vertices_wcs']=[[0,2,0],[10,2,0]]
  r=discover(c);self.assertFalse(r['bindings'])
  self.assertEqual(r['leader_diagnostics'][0]['arrow_to_nearest_edge_distance'],2)
 def test_escapes(self):
  decoded='S\\P中文 "引线" C:\\cad'
  serialized=json.dumps(decoded,ensure_ascii=False)
  c=self.context(HEADER.replace('Text_RAW="S"','Text_RAW='+serialized))
  a=c['annotations'][0];self.assertEqual(a['raw_serialized_text'],serialized)
  self.assertEqual(a['decoded_text'],decoded)
  e=discover(c)['evidence'][0];self.assertEqual(e['normalized_text'],'S\n中文 "引线" C:\\cad')
  self.assertEqual(e['raw_serialized_text'],serialized)
 def test_cp936_and_wrong_encoding(self):
  c=self.context(HEADER.replace('Text_RAW="S"','Text_RAW="S中文"'),encoding='cp936')
  self.assertEqual(c['annotations'][0]['decoded_text'],'S中文')
  with self.assertRaises(UnicodeDecodeError):load_report(self.path,encoding='utf-8')
 def test_manifest_valid_and_provenance(self):
  self.context();m=Path(self.tmp.name)/'manifest.json';write_manifest(self.path,m)
  c=load_report(self.path,'synthetic-project',manifest=m)
  r=discover(c);self.assertEqual(c['report_integrity'],'verified')
  p=r['bindings'][0]['provenance'][-1]
  self.assertEqual(p['leader_handle'],'L1');self.assertEqual(p['annotation_identity']['handle'],'A1')
  self.assertEqual(p['verified_report_sha256'],hashlib.sha256(self.path.read_bytes()).hexdigest())
 def test_manifest_missing_is_not_verified(self):
  c=self.context();self.assertEqual(c['report_integrity'],'unavailable/legacy')
  self.assertNotIn('verified_report_sha256',c['provenance'][0])
 def test_manifest_mismatch(self):
  self.context();m=Path(self.tmp.name)/'manifest.json';value=write_manifest(self.path,m)
  for field,bad in [('report_sha256','0'*64),('report_bytes',1),('encoding','cp936'),('report_file','foreign.txt'),('report_identity',{})]:
   mutated=copy.deepcopy(value);mutated[field]=bad;m.write_text(json.dumps(mutated),encoding='utf-8')
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'manifest'):load_report(self.path,manifest=m)
 def test_verifier_optimized_requires_manifest(self):
  self.context();tool=Path(__file__).with_name('verify_real_leader_report.py')
  p=subprocess.run([sys.executable,'-B','-O',str(tool),str(self.path)],capture_output=True)
  self.assertNotEqual(p.returncode,0);self.assertIn(b'manifest',p.stderr.lower())
 def test_current_direct_context_and_input_unchanged(self):
  c=self.context();before=copy.deepcopy(c)
  self.assertEqual(discover(c)['bindings'][0]['target_id'],'E1');self.assertEqual(c,before)
 def test_real_exporter_serialization_fixture(self):
  fixture=Path(__file__).resolve().parents[1]/'fixtures/exporter-string-escapes-v1.txt'
  data=fixture.read_bytes();meta=json.loads(fixture.with_suffix('.json').read_text(encoding='utf-8'))
  self.assertEqual(hashlib.sha256(data).hexdigest(),meta['report_sha256'])
  raw=data.decode(meta['encoding'])
  self.assertEqual(decode_exported_string(serialized_field(raw,'Text_RAW')),'S\\P中文 "引线" C:\\cad')
  self.assertEqual(decode_exported_string(serialized_field(raw,'Controls')),'a\nb\rc\td')
 def test_current_duplicate_records(self):
  c=self.context();c['annotations']*=2;c['leaders']*=2
  r=discover(c);self.assertEqual(len(r['evidence']),1);self.assertEqual(len(r['bindings']),1)
 def test_current_codes_and_no_reverse_spec_inference(self):
  for raw,codes in [('S',['S']),('S+D',['S+D']),('WDZN-RYJS-2×1.5 JDG20',[])]:
   with self.subTest(raw=raw):
    c=self.context(HEADER.replace('Text_RAW="S"','Text_RAW='+json.dumps(raw,ensure_ascii=False)))
    self.assertEqual(discover(c)['bindings'][0]['line_codes'],codes)
 def test_current_conflicting_codes(self):
  c=self.context();a=copy.deepcopy(c['annotations'][0]);a.update(handle='A2',raw_text='S+D',decoded_text='S+D')
  c['annotations'].append(a);leader=copy.deepcopy(c['leaders'][0]);leader.update(handle='L2',annotation_handle='A2')
  c['leaders'].append(leader)
  self.assertEqual(discover(c)['edge_summaries']['E1']['selection_status'],'conflicting')
 def test_current_bounded_and_unbounded_rest(self):
  c=self.context(HEADER.replace('Text_RAW="S"','Text_RAW="JDG20,余同"'))
  r=discover(c);self.assertEqual(r['propagation_roots'][0]['root_status'],'supported')
  self.assertEqual(r['propagation_roots'][0]['propagation_scope_status'],'unresolved')
  c['bounded_groups']=[{'annotation_handle':'A1','parent_path':[],'root_target_id':'E1',
      'bounded_set':[{'target_id':'E1','target_type':'edge'}],'propagation_relation':'synthetic bounded group',
      'scope_boundary':'synthetic boundary','termination_condition':'stop at boundary','status':'supported','provenance':['synthetic']}]
  self.assertEqual(discover(c)['propagation_roots'][0]['propagation_scope_status'],'supported')
 def test_current_z_unresolved(self):
  c=self.context();c['targets'][0]['geometry']['vertices_wcs']=[[0,0,3000],[10,0,3000]]
  b=discover(c)['bindings'][0];self.assertEqual(b['binding_status'],'supported')
  self.assertEqual(b['z_semantics'],'unresolved');self.assertEqual(b['geometric_basis']['xyz_distance'],3000)
 def test_missing_arrow_diagnostic(self):
  c=self.context();c['leaders'][0]['arrow_wcs']=None
  r=self.rejected(c,'arrow');self.assertFalse(r['leader_diagnostics'][0]['arrow_present'])
  self.assertIsNone(r['leader_diagnostics'][0]['arrow_to_nearest_edge_distance'])
 def test_unsupported_escape_keeps_raw_but_no_binding(self):
  c=self.context(HEADER.replace('Text_RAW="S"','Text_RAW="S\\q"'))
  self.assertEqual(c['annotations'][0]['text_decode_status'],'unresolved')
  self.assertEqual(c['annotations'][0]['raw_serialized_text'],'"S\\q"')
  self.rejected(c,'annotation_text')
 def test_direct_foreign_identity(self):
  c=self.context();c['leaders'][0]['source_drawing']='foreign.dwg'
  self.rejected(c,'identity')
 def test_current_text_type(self):
  c=self.context(HEADER.replace('DXF_Type="MTEXT"','DXF_Type="TEXT"'),BODY.replace('AnnotationType="MTEXT"','AnnotationType="TEXT"'))
  self.assertEqual(len(discover(c)['bindings']),1) # synthetic only, not real TEXT support proof
 def test_unknown_version_manifest_records_but_does_not_approve(self):
  self.context(body=BODY.replace('LeaderEvidenceVersion="1"','LeaderEvidenceVersion="999"'))
  m=Path(self.tmp.name)/'manifest.json';write_manifest(self.path,m)
  c=load_report(self.path,manifest=m);self.assertEqual(c['report_integrity'],'verified')
  self.rejected(c,'version')
 def test_verifier_optimized_manifest_tampering(self):
  self.context();m=Path(self.tmp.name)/'manifest.json';value=write_manifest(self.path,m)
  value['report_sha256']='0'*64;m.write_text(json.dumps(value),encoding='utf-8')
  tool=Path(__file__).with_name('verify_real_leader_report.py')
  p=subprocess.run([sys.executable,'-B','-O',str(tool),str(self.path),'--manifest',str(m)],capture_output=True)
  self.assertNotEqual(p.returncode,0);self.assertIn(b'manifest mismatch',p.stderr.lower())

if __name__=='__main__':unittest.main()
