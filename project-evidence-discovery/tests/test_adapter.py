import json,sys,tempfile,unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(MODULE))
from annotations import load_report
from discovery import discover
from test_discovery import context,run

class AdapterTests(unittest.TestCase):
 def report(self,leader):
  raw='''DWG="地下车库.dwg"
EntityHandle="A1"
DXF_Type="TEXT"
Text_RAW="S+D"
Insertion_WCS=(5 5 0)
EntityHandle="E1"
DXF_Type="LINE"
Start_WCS=(0 0 0)
End_WCS=(10 0 0)
EntityHandle="L1"
'''+leader
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'report.txt';p.write_text(raw,encoding='utf-8')
   return load_report(p)
 def test_native_leader_stable_handle(self):
  c=self.report('''DXF_Type="LEADER"
Raw_DXF=(340 . "A1")
Raw_DXF=(71 . 1)
Raw_DXF=(10 5 0 0)
Raw_DXF=(10 5 5 0)
''')
  self.assertEqual(discover(c)['bindings'][0]['target_id'],'E1')
 def test_runtime_ename_not_handle(self):
  c=self.report('''DXF_Type="LEADER"
Raw_DXF=(340 . <Entity name: A1>)
Raw_DXF=(71 . 1)
Raw_DXF=(10 5 0 0)
Raw_DXF=(10 5 5 0)
''')
  self.assertFalse(discover(c)['bindings'])
 def test_mleader_explicit_exported_chain(self):
  c=self.report('''DXF_Type="MLEADER"
AnnotationHandle="A1"
Arrow_WCS=(5 0 0)
LeaderVertex_WCS=(5 0 0)
LeaderVertex_WCS=(5 5 0)
''')
  self.assertEqual(discover(c)['bindings'][0]['line_codes'],['S+D'])
 def test_mleader_raw_ambiguous_not_parsed_as_leader(self):
  c=self.report('''DXF_Type="MLEADER"
Raw_DXF=(340 . "A1")
Raw_DXF=(10 5 0 0)
''')
  self.assertFalse(discover(c)['bindings'])
 def test_arrow_must_belong_to_exported_geometry(self):
  c=context();c['leaders'][0]['vertices_wcs']=[[5,100,0],[5,300,0]]
  self.assertFalse(run(c)['bindings'])
 def test_z_not_physical_disconnection(self):
  c=context();c['targets'][0]['geometry']['vertices_wcs']=[[0,0,3000],[10,0,3000]]
  b=run(c)['bindings'][0];self.assertEqual(b['binding_status'],'supported')
  self.assertEqual(b['geometric_basis']['xyz_distance'],3000)
 def test_missing_polyline_bulges_not_assumed_straight(self):
  c=context();c['targets'][0]['geometry']['type']='LWPOLYLINE'
  self.assertFalse(run(c)['bindings'])
 def test_conflicting_duplicates_cannot_keep_positive(self):
  c=context('JDG20,余同');a=dict(c['annotations'][0]);a['raw_text']='JDG25,余同';c['annotations'].append(a)
  r=run(c);self.assertEqual(r['bindings'][0]['binding_status'],'conflicting')
  self.assertEqual(r['propagation_roots'][0]['root_status'],'conflicting')
  self.assertEqual(r['edge_summaries']['E']['direct_binding_count'],0)
 def test_system_membership_remains_candidate(self):
  c=context('报警总线',False);c['memberships']=[{'annotation_handle':'T','target_id':'D','target_type':'device','membership_kind':'system',
    'geometric_basis':'verified bounded context','provenance':['fixture']}]
  m=run(c)['membership_candidates'][0];self.assertEqual(m['relation'],'system_membership_candidate');self.assertEqual(m['binding_status'],'partial')

if __name__=='__main__':unittest.main()
