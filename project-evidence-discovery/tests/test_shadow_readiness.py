"""Shadow boundary adversaries; synthetic reports are not project authorization."""
import copy
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from annotations import load_report
from discovery import discover
from report_manifest import write_manifest
from test_leader_v1 import HEADER, BODY

class ShadowReadiness(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.p=Path(self.tmp.name)/'report.txt';self.p.write_text(HEADER+BODY,encoding='utf-8')
 def context(self):return load_report(self.p,'synthetic-project')
 def bid(self,c):return discover(c)['bindings'][0]['binding_id']
 def shadow(self,**kw):return importlib.import_module('resolve').discover_shadow(self.p,project_id='synthetic-project',**kw)
 def manifest(self):return write_manifest(self.p,Path(self.tmp.name)/'manifest.json')
 def test_M1_path(self):
  a=self.bid(self.context());p=self.p.parent/'other.txt';p.write_bytes(self.p.read_bytes())
  self.assertEqual(a,self.bid(load_report(p,'synthetic-project')))
 def test_M1_manifest(self):
  a=self.bid(self.context());self.assertEqual(a,self.bid(load_report(self.p,'synthetic-project',manifest=self.manifest())))
 def test_M1_unrelated_entity(self):
  a=self.bid(self.context());self.p.write_text(HEADER+BODY+'EntityHandle="E99"\nDXF_Type="LINE"\nStart_WCS=(100 100 0)\nEnd_WCS=(101 100 0)\n',encoding='utf-8')
  self.assertEqual(a,self.bid(self.context()))
 def test_M1_integrity_representation(self):
  c=self.context();a=self.bid(c);c['report_integrity']='verified';c['provenance'][0]['verified_report_sha256']='changed-representation'
  self.assertEqual(a,self.bid(c))
 def test_M1_drawing_control(self):
  a=self.bid(self.context());self.p.write_text((HEADER+BODY).replace('synthetic-leader.dwg','other.dwg'),encoding='utf-8');self.assertNotEqual(a,self.bid(self.context()))
 def test_M1_project_control(self):
  self.assertNotEqual(self.bid(self.context()),self.bid(load_report(self.p,'other-project')))
 def test_validated_identity_preserved(self):
  r=discover(self.context());ident=r['leader_diagnostics'][0]['validated_annotation_identity']
  self.assertEqual(ident,{'handle':'A1','parent_path':[],'type':'MTEXT','source_drawing':'synthetic-leader.dwg','project_id':'synthetic-project'})
  self.assertEqual(r['bindings'][0]['provenance'][-1]['annotation_identity'],ident)
 def test_M2_annotation_identity(self):
  c=self.context();a=copy.deepcopy(c['annotations'][0]);a.update(parent_path=['X'],type='DIMENSION');c['annotations'].append(a)
  c['leaders'][0]['annotation_parent_path']=['X'];r=discover(c)
  self.assertEqual(r['bindings'],[]);self.assertIn('annotation_type',r['leader_diagnostics'][0]['failure_reasons'])
 def test_L1_missing_identity(self):
  for key in ('source_drawing','project_id','parent_path'):
   with self.subTest(key=key):
    c=self.context();del c['leaders'][0][key];self.assertEqual(discover(c)['bindings'],[])
 def test_L2_missing_decode(self):
  c=self.context();del c['annotations'][0]['text_decode_status'];self.assertEqual(discover(c)['bindings'],[])
 def test_explicit_null_project(self):
  c=load_report(self.p);self.assertIn('project_id',c['leaders'][0]);self.assertIsNone(c['leaders'][0]['project_id']);self.assertEqual(len(discover(c)['bindings']),1)
 def test_M3_missing_manifest(self):
  with self.assertRaisesRegex(ValueError,'manifest'):self.shadow()
 def test_M3_forged_context(self):
  c=self.context();c['report_integrity']='verified'
  with self.assertRaises((TypeError,ValueError)):importlib.import_module('resolve').discover_shadow(c,manifest=self.manifest())
 def test_M3_manifest_fields(self):
  m=self.manifest()
  for field,value in [('report_sha256','0'*64),('report_bytes',0),('encoding','cp936'),('report_identity',{}),('hash_scope','anything'),('report_file','other.txt')]:
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'manifest'):
    bad=copy.deepcopy(m);bad[field]=value;self.shadow(manifest=bad)
 def test_M3_verified_positive(self):
  r=self.shadow(manifest=self.manifest());self.assertEqual(r['report_integrity'],'verified');self.assertEqual(len(r['bindings']),1)
 def test_L3_conflict_diagnostic(self):
  c=self.context();a=c['annotations'][0];a.update(raw_text='JDG20,余同',decoded_text='JDG20,余同')
  other=copy.deepcopy(a);other.update(raw_text='JDG25,余同',decoded_text='JDG25,余同');c['annotations'].append(other)
  r=discover(c);self.assertFalse(any(b['binding_status']=='supported' for b in r['bindings']))
  self.assertEqual(r['evidence'][0]['binding_status'],'conflicting');self.assertEqual(r['propagation_roots'][0]['root_status'],'conflicting')
  self.assertIn('annotation_conflict',r['leader_diagnostics'][0]['failure_reasons'])
 def test_current_chinese_adjacent(self):
  self.p.write_text((HEADER+BODY).replace('Text_RAW="S"','Text_RAW="S报警总线"'),encoding='utf-8')
  self.assertEqual(discover(self.context())['bindings'][0]['line_codes'],['S'])
 def test_current_root_unknown_scope(self):
  self.p.write_text((HEADER+BODY).replace('Text_RAW="S"','Text_RAW="JDG20,余同"'),encoding='utf-8');r=discover(self.context())
  self.assertEqual(r['propagation_roots'][0]['propagation_scope_status'],'unresolved')
  self.assertIn('propagation_boundary_unknown',r['evidence'][0]['discovery_gaps']);self.assertEqual(r['evidence'][0]['discovery_status'],'partial')
 def test_legacy_native_rejected(self):
  c=self.context();c['leaders'][0].pop('evidence_version');r=discover(c);self.assertFalse(r['bindings']);self.assertIn('version',r['leader_diagnostics'][0]['failure_reasons'])
 def test_legacy_mleader_rejected(self):
  c=self.context();c['leaders'][0]['type']='MLEADER';r=discover(c);self.assertFalse(r['bindings']);self.assertIn('mleader_object_chain_validated',r['leader_diagnostics'][0]['failure_reasons'])
