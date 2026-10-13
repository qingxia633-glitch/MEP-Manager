import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from annotations import load_report
from discovery import discover
from resolve import discover_shadow
from report_manifest import write_manifest
from test_leader_v1 import HEADER,BODY

class FinalShadowEntry(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.p=Path(self.tmp.name)/'report.txt';self.p.write_text(HEADER+BODY,encoding='utf-8')
 def context(self):return load_report(self.p,'P')
 def manifest(self):return write_manifest(self.p,Path(self.tmp.name)/'manifest.json')
 def association(self):
  return {'annotation_handle':'A1','parent_path':[],'target_id':'E1','status':'supported',
          'geometric_basis':{'point_wcs':[5,0,0]},'provenance':['synthetic A']}
 def assert_conflict(self,r):
  self.assertTrue(r['bindings']);self.assertEqual(len(r['bindings']),1)
  b=r['bindings'][0];self.assertEqual(b['binding_status'],'conflicting')
  self.assertIn('binding_conflict',b['diagnostics']);self.assertEqual(len(b['conflicting_variants']),2)
  self.assertTrue(all(v['binding_status']=='conflicting' for v in b['conflicting_variants']))
  self.assertEqual(r['edge_summaries']['E1']['direct_binding_count'],0)
  self.assertEqual(r['evidence'][0]['binding_status'],'conflicting')
 def test_duplicate_association_conflict(self):
  c=self.context();c['leaders']=[];a=self.association();b=copy.deepcopy(a)
  b['geometric_basis']['point_wcs']=[6,0,0];b['provenance']=['synthetic B'];c['object_associations']=[a,b]
  self.assert_conflict(discover(c))
 def test_duplicate_leader_handle_conflict(self):
  c=self.context();b=copy.deepcopy(c['leaders'][0]);b['arrow_wcs']=[6,0,0];b['vertices_wcs'][0]=[6,0,0];c['leaders'].append(b)
  self.assert_conflict(discover(c))
 def test_exact_duplicate(self):
  c=self.context();c['leaders']*=2;r=discover(c);self.assertEqual(len(r['bindings']),1);self.assertEqual(r['bindings'][0]['binding_status'],'supported')
 def test_exact_association_duplicate(self):
  c=self.context();c['leaders']=[];a=self.association();c['object_associations']=[a,copy.deepcopy(a)]
  r=discover(c);self.assertEqual(len(r['bindings']),1);self.assertEqual(r['bindings'][0]['binding_status'],'supported')
 def test_conflict_blocks_propagation(self):
  c=self.context();c['annotations'][0].update(raw_text='JDG20,余同',decoded_text='JDG20,余同')
  b=copy.deepcopy(c['leaders'][0]);b['arrow_wcs']=[6,0,0];b['vertices_wcs'][0]=[6,0,0];c['leaders'].append(b)
  r=discover(c);self.assertEqual(r['propagation_roots'][0]['root_status'],'conflicting')
  self.assertEqual(r['propagation_roots'][0]['bounded_set'],[])
 def test_conflicting_leader_different_targets(self):
  c=self.context();b=copy.deepcopy(c['leaders'][0]);b['arrow_wcs']=[6,20,0];b['vertices_wcs'][0]=[6,20,0];c['leaders'].append(b)
  t=copy.deepcopy(c['targets'][0]);t.update(id='E2');t['geometry']['vertices_wcs']=[[0,20,0],[10,20,0]];c['targets'].append(t)
  r=discover(c);self.assertEqual(len(r['bindings']),2);self.assertTrue(all(b['binding_status']=='conflicting' for b in r['bindings']))
 def test_provenance_only_duplicate(self):
  c=self.context();b=copy.deepcopy(c['leaders'][0]);b['provenance']=[{'path':'different','report_sha256':'other'}];c['leaders'].append(b)
  r=discover(c);self.assertEqual(len(r['bindings']),1);self.assertEqual(r['bindings'][0]['binding_status'],'supported')
 def test_shadow_missing_project(self):
  with self.assertRaisesRegex(ValueError,'project_id'):discover_shadow(self.p,manifest=self.manifest())
 def test_shadow_invalid_project(self):
  m=self.manifest()
  for project in (None,'','  ',123):
   with self.subTest(project=project),self.assertRaisesRegex(ValueError,'project_id'):discover_shadow(self.p,manifest=m,project_id=project)
 def test_non_top_level(self):
  self.p.write_text((HEADER+BODY).replace('ModelSpaceTopLevel="included"','ModelSpaceTopLevel="unknown"'),encoding='utf-8')
  r=discover_shadow(self.p,manifest=self.manifest(),project_id='P')
  self.assertEqual(r['report_integrity'],'verified');self.assertEqual(r['binding_count'],0)
  self.assertEqual(r['acquisition_scope_status'],'not_eligible');self.assertFalse(r['shadow_evaluable'])
  self.assertEqual(r['zero_binding_reason'],'acquisition_scope_not_top_level')
 def test_valid_no_target(self):
  self.p.write_text((HEADER+BODY).replace('Start_WCS=(0 0 0)','Start_WCS=(0 20 0)').replace('End_WCS=(10 0 0)','End_WCS=(10 20 0)'),encoding='utf-8')
  r=discover_shadow(self.p,manifest=self.manifest(),project_id='P');self.assertTrue(r['shadow_evaluable'])
  self.assertEqual(r['binding_count'],0);self.assertEqual(r['zero_binding_reason'],'no_target_match')
 def test_valid_no_supported_leader(self):
  self.p.write_text(HEADER,encoding='utf-8');r=discover_shadow(self.p,manifest=self.manifest(),project_id='P')
  self.assertTrue(r['shadow_evaluable']);self.assertEqual(r['zero_binding_reason'],'no_supported_leader_evidence')
 def test_verified_annotation_conflict_zero(self):
  self.p.write_text(HEADER+BODY+'EntityHandle="A1"\nDXF_Type="MTEXT"\nText_RAW="S+D"\nInsertion_WCS=(5 5 0)\n',encoding='utf-8')
  r=discover_shadow(self.p,manifest=self.manifest(),project_id='P')
  self.assertEqual(r['binding_count'],0);self.assertEqual(r['zero_binding_reason'],'ambiguous_or_conflicting_evidence')
 def test_positive_observable(self):
  r=discover_shadow(self.p,manifest=self.manifest(),project_id='P')
  self.assertEqual(r['binding_count'],1);self.assertIsNone(r['zero_binding_reason']);self.assertTrue(r['shadow_evaluable'])
 def test_different_object_identity(self):
  c=self.context();a=discover(c)['bindings'][0]['binding_id'];c['targets'][0]['id']='different'
  self.assertNotEqual(a,discover(c)['bindings'][0]['binding_id'])
