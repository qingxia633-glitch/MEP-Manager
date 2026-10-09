import copy,json,sys,tempfile,unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MODULE))
from discovery import discover
from annotations import load_report, normalize_text, corrected_reference

DRAWING='地下车库火灾报警平面图.dwg'
def context(text='S',leader=True):
 c={'drawing_ref':DRAWING,'provenance':['synthetic fixture'],
    'annotations':[{'handle':'T','type':'TEXT','raw_text':text,'position_wcs':[5,300,0],'provenance':['fixture']}],
    'targets':[{'id':'E','target_type':'edge','geometry':{'type':'LINE','vertices_wcs':[[0,0,0],[10,0,0]],'complete':True},'provenance':['fixture']}],
    'leaders':[],'object_associations':[],'bounded_groups':[],'memberships':[]}
 if leader:c['leaders']=[{'handle':'L','annotation_handle':'T','association_status':'explicit',
                         'arrow_wcs':[5,0,0],'vertices_wcs':[[5,0,0],[5,300,0]],'provenance':['fixture']}]
 return c
def run(c):return discover(c,xy_tolerance=.001,nearby_distance=1000)

class DiscoveryTests(unittest.TestCase):
 def test_leader_binding(self):
  r=run(context());self.assertEqual(r['bindings'][0]['binding_method'],'leader_binding')
  self.assertEqual(r['bindings'][0]['target_id'],'E')
 def test_nearby_never_binding(self):
  r=run(context(leader=False));self.assertFalse(r['bindings'])
  self.assertEqual(r['evidence'][0]['binding_method'],'nearby_context')
 def test_s_selection(self):self.assertEqual(run(context())['bindings'][0]['line_codes'],['S'])
 def test_sd_selection(self):self.assertEqual(run(context('S+D'))['bindings'][0]['line_codes'],['S+D'])
 def test_competing_codes(self):
  c=context();a=copy.deepcopy(c['annotations'][0]);a.update(handle='T2',raw_text='S+D');c['annotations'].append(a)
  l=copy.deepcopy(c['leaders'][0]);l.update(handle='L2',annotation_handle='T2');c['leaders'].append(l)
  r=run(c);self.assertEqual(r['edge_summaries']['E']['selection_status'],'conflicting')
 def test_spec_not_s(self):self.assertEqual(run(context('WDZN-RYJS-2×1.5 JDG20'))['bindings'][0]['line_codes'],[])
 def test_chinese_adjacent_specification_keywords(self):
  r=run(context('采用JDG20沿顶板CC',False));self.assertEqual(r['evidence'][0]['evidence_category'],['specification'])
 def test_chinese_adjacent_s_label(self):
  self.assertEqual(run(context('标注S+D线路'))['bindings'][0]['line_codes'],['S+D'])
 def test_bounded_rest(self):
  c=context('JDG20,余同');c['bounded_groups']=[{'annotation_handle':'T','root_target_id':'E','bounded_set':[{'target_id':'E','target_type':'edge'}],
      'propagation_relation':'explicit group','scope_boundary':'boundary:1','termination_condition':'stop at boundary',
      'status':'supported','provenance':['fixture']}]
  p=run(c)['propagation_roots'][0];self.assertEqual(p['root_status'],'supported');self.assertEqual(p['propagation_scope_status'],'supported')
 def test_root_known_scope_unknown(self):
  r=run(context('JDG20,余同'));self.assertEqual(r['propagation_roots'][0]['root_status'],'supported')
  self.assertIn('propagation_boundary_unknown',r['evidence'][0]['discovery_gaps'])
  self.assertEqual(r['evidence'][0]['discovery_status'],'partial')
 def test_root_unknown(self):
  r=run(context('JDG25,余同',False));self.assertEqual(r['propagation_roots'][0]['root_status'],'unresolved')
 def test_nearby_sd_unknown(self):self.assertFalse(run(context('S+D',False))['bindings'])
 def test_region_membership_typed(self):
  c=context('防火分区一',False);c['memberships']=[{'annotation_handle':'T','target_id':'D','target_type':'device',
    'region_id':'region1','geometric_basis':{'source':'independent region relation'},'provenance':['fixture']}]
  r=run(c);self.assertEqual(r['membership_candidates'][0]['relation'],'device_in_region')
  self.assertFalse(any(x['relation']=='edge_in_region' for x in r['membership_candidates']))
 def test_duplicate_dedup(self):
  c=context();c['annotations']*=2;c['leaders']*=2
  r=run(c);self.assertEqual(len(r['evidence']),1);self.assertEqual(len(r['bindings']),1)
 def test_raw_unicode_preserved(self):
  raw='报警二总线\\PS+D';c=context(raw);r=run(c)
  self.assertEqual(r['evidence'][0]['raw_text'],raw);self.assertEqual(r['evidence'][0]['source_drawing'],DRAWING)
  self.assertIn('报警二总线',json.dumps(r,ensure_ascii=False))
 def test_arrow_not_landing(self):
  c=context();c['leaders'][0]['arrow_wcs']=[5,100,0];c['leaders'][0]['vertices_wcs']=[[5,100,0],[5,0,0]]
  self.assertFalse(run(c)['bindings'])
 def test_association_required(self):
  c=context();c['leaders'][0]['association_status']='unknown';self.assertFalse(run(c)['bindings'])
 def test_cross_drawing_no_binding(self):
  c=context();c['leaders'][0]['source_drawing']='other.dwg';self.assertFalse(run(c)['bindings'])
 def test_multiple_targets_ambiguous(self):
  c=context();e=copy.deepcopy(c['targets'][0]);e['id']='E2';c['targets'].append(e)
  r=run(c);self.assertTrue(all(b['binding_status']=='partial' for b in r['bindings']))
 def test_curve_not_chord(self):
  c=context();c['targets'][0]['geometry'].update(type='LWPOLYLINE',bulges=[1,0])
  self.assertFalse(run(c)['bindings'])
 def test_attribute_owner_not_nearby_edge(self):
  c=context('S',False);c['annotations'][0].update(type='ATTRIB',parent_handle='D',association_status='explicit')
  c['targets'].append({'id':'D','target_type':'device','provenance':['fixture']})
  r=run(c);self.assertEqual([b['target_id'] for b in r['bindings']],['D'])
 def test_no_approval_or_quantity(self):
  r=run(context());s=json.dumps(r)
  self.assertNotIn('project_specific_status',s);self.assertNotIn('design_net_quantity_eligible',s)
 def test_unknown_z_kept(self):self.assertEqual(run(context())['bindings'][0]['z_semantics'],'unresolved')
 def test_missing_leader_fields(self):
  c=context();del c['leaders'][0]['arrow_wcs'];r=run(c)
  self.assertFalse(r['bindings']);self.assertIn('leader_geometry_unavailable',r['evidence'][0]['discovery_gaps'])
 def test_invalid_tolerance(self):
  with self.assertRaises(ValueError):discover(context(),xy_tolerance=0)
 def test_correction_is_scoped(self):
  corr={'historical_value':'????.dwg','corrected_value':DRAWING,'status':'approved','target_object_ids':['o1'],'provenance':['fixture'],'correction_id':'c1'}
  self.assertEqual(corrected_reference('????.dwg','o1',[corr])[0],DRAWING)
  with self.assertRaises(ValueError):corrected_reference('????.dwg','other',[corr])
 def test_dimension_like_no_inferred_binding(self):
  c=context('JDG20',False);c['annotations'][0]['type']='DIMENSION';self.assertFalse(run(c)['bindings'])

if __name__=='__main__':unittest.main()
