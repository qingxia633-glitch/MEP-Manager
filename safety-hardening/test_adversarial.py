"""Safe expectations established before implementation changes. Run with -B."""
import copy,importlib.util,json,sys,tempfile,unittest
from decimal import localcontext
from pathlib import Path
from unittest.mock import patch,MagicMock
from fixtures import item,plan,policy,seal
ROOT=Path(__file__).resolve().parents[1]
def load(folder,file='resolver.py'):
 for name in ('resolver','evidence','model','rules','annotations','bindings'):sys.modules.pop(name,None)
 sys.path.insert(0,str(ROOT/folder))
 spec=importlib.util.spec_from_file_location(folder.replace('-','_')+file.replace('.','_'),ROOT/folder/file)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Safety(unittest.TestCase):
 def test_S1_cross_category(self):
  m=load('quantity-eligibility')
  for kind in ('vertical','other'):
   x=item();g=copy.deepcopy(x['adjustments']['transition']);g['items']=g['items'][:1];g['items'][0]['adjustment_id']='new-id';x['adjustments'][kind]=g
   self.assertNotEqual(m.resolve_eligibility(x)['quantity_eligibility_status'],'eligible')
 def test_S2_replay_contract(self):
  m=load('design-net-quantity','builder.py');p=plan();q=m.build(p,[])['quantity']
  for change in ('owner','device','evidence','assumption','composition','correction'):
   with self.subTest(change=change):
    x=copy.deepcopy(p)
    if change=='owner':x['owned_adjustments'][0]['owner']['edge_handle']='other'
    if change=='device':x['owned_adjustments'][0]['device']='other'
    if change=='evidence':x['source_evidence_hashes']['synthetic-review']['sha256']='d'*64
    if change=='assumption':x['assumptions']=[{'id':'changed','value':1}]
    if change=='composition':
     x['base_path']['value']='10.1';x['owned_adjustments'][0]['length']='0.1'
     for t,v in zip(x['unit_execution_contract']['components'],['10.1','0.1','0.3']):t.update(original_value=v,normalized_value=v)
    if change=='correction':x['corrections_applied']={'evidence':None,'changed_paths':['/binding/drawing_ref']}
    self.assertNotEqual(m.replay_validate(seal(x),q)['status'],'replay_matched')
 def test_S2_legacy_not_full_match(self):
  m=load('design-net-quantity','builder.py');p=plan();q=m.build(p,[])['quantity'];legacy={k:q[k] for k in ('scope','quantity_kind','approved_semantic_role','specification','installation_method','computed_quantity')};legacy['multiplier']=1
  self.assertNotEqual(m.replay_validate(p,legacy)['status'],'replay_matched')
 def test_S3_cli_no_overwrite(self):
  for folder in ('geometry-connection','device-role','candidate-semantic','project-evidence-gate','quantity-eligibility'):
   for alias in (False,True):
    with self.subTest(module=folder,input_is_output=alias),tempfile.TemporaryDirectory() as d:
     m=load(folder,'resolve.py');src=Path(d)/'input.json';src.write_text('{}');out=src if alias else Path(d)/'existing.json';out.write_text('{}');before=out.read_bytes()
     fake=MagicMock();fake.entities={'E':{'type':'LINE','vertices':[[0,0,0],[1,0,0]]}}
     names={'DrawingContext':MagicMock(from_reports=lambda *a:fake),'RoleContext':MagicMock(from_reports=lambda *a:fake),'resolve_connection':lambda *a:{'changed':True},'resolve_device_role':lambda *a:{'changed':True},'resolve_candidate':lambda *a:{'changed':True},'load_rules':lambda *a:{},'evaluate_semantics':lambda *a:{'provenance':{}},'load_bundle':lambda *a:{},'load_evidence':lambda *a:{'objects':[]}}
     args={'geometry-connection':['--snapshot',str(src),'--edge','E','--target','I','--endpoint-index','0','--tolerance','0.001'], 'device-role':['--snapshot',str(src),'--device','I'],'candidate-semantic':['--input',str(src),'--rules',str(src)],'project-evidence-gate':['--candidate',str(src),'--evidence',str(src),'--project-id','P','--drawing-ref','D'],'quantity-eligibility':['--input',str(src)]}[folder]
     with patch.dict(m.__dict__,{k:v for k,v in names.items() if k in m.__dict__}),patch.object(sys,'argv',['resolve',*args,'--output',str(out)]):
      try:m.main()
      except (FileExistsError,ValueError,SystemExit):pass
     self.assertEqual(out.read_bytes(),before)
 def test_S4_incomplete_plan(self):
  m=load('design-net-quantity','builder.py')
  for change in ('role','scope','dedup','provenance','binding'):
   with self.subTest(change=change):
    p=plan()
    if change=='role':p['approved_semantic_role']='unknown'
    if change=='scope':p['binding']={'project_id':'synthetic-project'}
    if change=='dedup':p['deduplication']['provenance']=[]
    if change=='provenance':p['owned_adjustments'][0]['provenance']=[]
    if change=='binding':p['base_path']['binding']['edge_handle']='wrong'
    self.assertNotEqual(m.build(seal(p),[])['status'],'built')
 def test_S5_metadata_duplicate(self):
  m=load('design-net-quantity','builder.py');p=plan();q=m.build(p,[])['quantity'];p['binding']['audit_note']='note'
  self.assertEqual(m.build(seal(p),[q])['status'],'duplicate_detected')
 def propagation(self):
  c={'project_id':'P','drawing_ref':'D'};t={'id':'E','kind':'edge'}
  r={'rule_id':'r','rule_version':'1','context':c,'binding_scope':'object','conditions':[{'condition_id':'a','channel':'object_facts','key':'a','expected':True}],'propagation_key':'rest','provenance':['test']}
  w={**c,'target_id':'E','target_kind':'edge','key':'a','value':True,'status':'supported','evidence_strength':'drawing_fact','provenance':['test']}
  p={**w,'key':'rest','source_annotation':'T','root_target':t,'propagation_relation':'group','bounded_set':[t],'propagation_boundary':{'status':'unresolved'},'termination_condition':{'status':'unknown'}}
  return r,{'context':c,'target_object':t,'object_facts':[w],'propagation_sources':[p]}
 def test_S6_unknown_boundary(self):
  m=load('project-rule-applicability');r,q=self.propagation();self.assertFalse(m.resolve(r,q)['may_submit_to_project_gate'])
 def test_S7_wrong_endpoint(self):
  m=load('geometry-connection');i={'handle':'I','type':'INSERT','block':'B','insertion':[0,0,0],'scale':[1,1,1],'rotation':0,'normal':[0,0,1],'dynamic':False}
  ctx=m.DrawingContext({'I':i,'A':{'type':'LINE','vertices':[[10,0,0],[20,0,0]]},'B-edge':{'type':'LINE','vertices':[[0,0,0],[1,0,0]]}},{'B':{'base':[0,0,0],'dynamic':False,'complete':True,'entities':[{'handle':'P','type':'POINT','point':[0,0,0]}]}},[])
  self.assertNotEqual(m.resolve_connection('A',[0,0,0],'I',ctx,.001)['geometric_connection_status'],'supported')
 def test_S8_malformed_targets(self):
  m=load('project-rule-applicability');r,q=self.propagation();r.pop('propagation_key');r['target_ids']='E-EXTRA'
  with self.assertRaises(ValueError):m.resolve(r,q)
 def test_G1_instance_path(self):
  m=load('project-evidence-discovery','discovery.py');c={'drawing_ref':'D','annotations':[{'handle':'T','parent_path':['I1'],'type':'TEXT','raw_text':'S'},{'handle':'T','parent_path':['I2'],'type':'TEXT','raw_text':'S'}],'targets':[{'id':'E','target_type':'edge','geometry':{'type':'LINE','complete':True,'vertices_wcs':[[0,0,0],[1,0,0]]}}],'leaders':[{'handle':'L','parent_path':['I1'],'annotation_handle':'T','association_status':'explicit','arrow_wcs':[0,0,0],'vertices_wcs':[[0,0,0],[0,1,0]],'provenance':['test']}]}
  result=m.discover(c);self.assertNotEqual(result['evidence'][1]['binding_status'],'supported')
 def test_G2_no_correction(self):
  e=load('quantity-eligibility');d=e.resolve_eligibility(item());m=load('quantity-eligibility','plan_v02.py')
  self.assertEqual(m.export_plan(d,'a'*64,None,policy())['schema_version'],'0.2')
 def test_G3_decimal_context(self):
  m=load('quantity-eligibility');x=item();g=x['geometry'];g['base_length']='123456789012345678901234567890';g['source_unit']='mm';g['conversion'].update(from_unit='mm',factor='0.001',converted_length='123456789012345678901234567.890');x['base_path']['value']=g['conversion']['converted_length'];statuses=[]
  for precision in (28,80):
   with localcontext() as c:c.prec=precision;statuses.append(m.resolve_eligibility(x)['quantity_eligibility_status'])
  self.assertEqual(statuses,['eligible','eligible'])
 def test_G4_cross_drawing(self):
  m=load('candidate-semantic');ctx={'project':'P','validation_area':'R'}
  endpoint={'geometry_connection':{'edge_handle':'E','target_handle':'D','geometric_connection_status':'supported','drawing_ref':'A'},'device_role':{'device_handle':'D','canonical_role':'smoke_detector','role_status':'supported','drawing_ref':'B'}}
  r={'rules':[{'kind':'role_pair','rule_id':'A','roles_A':['smoke_detector'],'roles_B':['smoke_detector'],'scope':ctx,'validation_status':'validated','candidate_role':'alarm_or_linkage_bus'}],'scope_keys':list(ctx),'confidence_policy':{'validated':'medium'}}
  out=m.resolve_candidate({'edge_handle':'E','scope':ctx,'endpoint_A':endpoint,'endpoint_B':copy.deepcopy(endpoint)},r);self.assertNotEqual(out['candidate_status'],'candidate')
 def test_G5_policy_source(self):
  m=load('device-role');c=m.RoleContext('D',{'I':{'block_name':'B','attributes':[]}},{},legends=[{'source_drawing':'approved-other.dwg','target_drawing':'D','target_block_name':'B','binding_verified':True,'binding_evidence_refs':['test'],'raw_value':'模块箱'}])
  c.legend_policy=seal({'policy_id':'P','version':'1','status':'approved','target_drawing':'D','allowed_sources':['approved-other.dwg'],'provenance':['project review']})
  self.assertEqual(m.resolve_device_role('I',c)['canonical_role'],'module_box')
if __name__=='__main__':unittest.main(verbosity=2)
