"""Synthetic contract inputs only; not BX evidence or host verification."""
import copy,sys,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'explicit-cross-sheet-reference'))
sys.path.insert(0,str(ROOT/'project-drawing-registry'))
sys.path.insert(0,str(ROOT/'project-evidence-discovery'))
from registry import content_hash
from references import scan, extract_text, validate_registry

def drawing(name,sha):
 b={'project_id':'P','drawing_ref':name,'report_sha256':sha*64,'source_dwg_sha256':None}
 return dict(b,instance_id=content_hash(b),report_identity={'drawing':name},logical_identity_status='unresolved')

def fixture(text='详见 EW-0073',target_count=1):
 src=drawing('source.dwg','a');targets=[drawing('target'+str(i)+'.dwg',str(i+1)) for i in range(target_count)]
 aliases=[{'kind':'drawing_number_candidate','value':'EW-0073','instance_id':d['instance_id'],'status':'partial','identifies_current_drawing':'unresolved','source_identity':{'project_id':'P','snapshot_id':d['report_sha256']},'provenance':[{'source_type':'report_bytes','sha256':d['report_sha256']}]} for d in targets]
 reg={'registry_version':1,'project_id':'P','drawing_instances':[src]+targets,'aliases':aliases}
 c={'project_id':'P','drawing_ref':'source.dwg','report_identity':src['report_identity'],'snapshot_id':'a'*64,'report_integrity':'verified','annotations':[],'table_evidence':[],'field_evidence':[],'leaders':[]}
 a={'handle':'A','type':'TEXT','project_id':'P','source_drawing':'source.dwg','parent_path':[],'decoded_text':text,'raw_serialized_text':json.dumps(text),'text_decode_status':'read','provenance':[{'sha256':'a'*64}]}
 c['annotations']=[a];return reg,c

class ReferencesTests(unittest.TestCase):
 def run_case(self,text='详见 EW-0073',n=1):
  r,c=fixture(text,n);return scan(r,[c])
 def test_explicit(self):self.assertEqual(self.run_case()['source_references'][0]['reference_extraction_status'],'supported')
 def test_cue_without_identifier(self):
  x=self.run_case('详见上级配电箱')['source_references'][0];self.assertEqual(x['target_identifier_status'],'unresolved');self.assertEqual(x['resolution_status'],'unresolved_target')
 def test_zero(self):self.assertEqual(self.run_case(n=0)['summary']['unresolved'],1)
 def test_one(self):self.assertEqual(self.run_case()['summary']['unique_registry_candidates'],1)
 def test_many(self):
  x=self.run_case(n=2)['source_references'][0];self.assertEqual(x['resolution_status'],'ambiguous');self.assertEqual(len(x['target_candidate_instance_ids']),2)
 def test_no_final_approval(self):self.assertEqual(self.run_case()['resolved_links'],[])
 def test_deterministic(self):self.assertEqual(self.run_case(),self.run_case())
 def test_source_id_excludes_target(self):self.assertEqual(self.run_case(n=0)['source_references'][0]['reference_id'],self.run_case(n=2)['source_references'][0]['reference_id'])
 def test_dedup(self):
  r,c=fixture();c['annotations']*=2;self.assertEqual(scan(r,[c,c])['summary']['source_reference_count'],1)
 def test_conflict(self):
  r,c=fixture();b=copy.deepcopy(c['annotations'][0]);b['decoded_text']='详见 EC-04';c['annotations'].append(b)
  x=scan(r,[c]);self.assertEqual(len(x['conflicts']),1);self.assertTrue(all(a['resolution_status']=='conflicting_source' for a in x['source_references']))
 def test_independent_sources(self):
  r,c=fixture();b=copy.deepcopy(c['annotations'][0]);b['handle']='B';c['annotations'].append(b);self.assertEqual(scan(r,[c])['summary']['source_reference_count'],2)
 def test_same_S(self):self.assertEqual(self.run_case('S')['source_references'],[])
 def test_equipment(self):self.assertEqual(self.run_case('区域分机 M2')['source_references'],[])
 def test_style_shape(self):
  r,c=fixture('');c['annotations'][0].update(color='red',layer='S',shape='circle');self.assertEqual(scan(r,[c])['source_references'],[])
 def test_foreign_project(self):
  r,c=fixture();c['project_id']='Q'
  with self.assertRaises(ValueError):scan(r,[c])
 def test_foreign_snapshot(self):
  r,c=fixture();c['snapshot_id']='f'*64
  with self.assertRaises(ValueError):scan(r,[c])
 def test_foreign_provenance(self):
  r,c=fixture();c['annotations'][0]['provenance']=[{'sha256':'f'*64}];self.assertEqual(scan(r,[c])['source_references'],[])
 def test_order(self):
  r,c=fixture();b=copy.deepcopy(c['annotations'][0]);b.update(handle='B',decoded_text='参见 EC-04');c['annotations'].append(b);a=scan(r,[c]);c['annotations'].reverse();self.assertEqual(a,scan(r,[c]))
 def test_punctuation_not_deleted(self):self.assertIsNone(extract_text('详见 EW - 0073')[0]['identifier_raw'])
 def test_dot_preserved(self):self.assertEqual(extract_text('详见 E-101.2')[0]['identifier_raw'],'E-101.2')
 def test_title(self):self.assertEqual(extract_text('详见火灾报警系统图')[0]['reference_type'],'drawing_title_reference')
 def test_multiple_numbers(self):self.assertEqual([x['identifier_raw'] for x in extract_text('详见 EW-0073、EC-04')],['EW-0073','EC-04'])
 def test_no_substring_number(self):self.assertIsNone(extract_text('详见 EW-0073A')[0]['identifier_raw'])
 def test_not_opinion(self):self.assertEqual(extract_text('设计意见'),[])
 def test_forged_target_approval(self):
  r,c=fixture();r['drawing_instances'][1]['logical_identity_status']='supported';self.assertEqual(scan(r,[c])['resolved_links'],[])
 def test_alias_foreign_hash(self):
  r,c=fixture();r['aliases'][0]['provenance'][0]['sha256']='f'*64
  with self.assertRaises(ValueError):scan(r,[c])
 def test_field_display_not_field_ref(self):self.assertEqual(self.run_case('SheetNumber EW-0073')['source_references'],[])
 def test_mtext_paragraphs(self):
  from mtext_structure import structure_record
  r,c=fixture('详见 EW-0073\\P参见 EC-04');a=c['annotations'][0];a['type']='MTEXT';a['mtext_structure']=structure_record(a,c['snapshot_id'])
  x=scan(r,[c]);self.assertEqual(len(x['source_references']),2);self.assertTrue(all(e['source_subelement_identity'] is not None for e in x['source_references']))
 def test_mtext_unknown_control_partial(self):
  from mtext_structure import structure_record
  r,c=fixture('\\Z详见 EW-0073');a=c['annotations'][0];a['type']='MTEXT';a['mtext_structure']=structure_record(a,c['snapshot_id'])
  self.assertEqual(scan(r,[c])['source_references'][0]['reference_extraction_status'],'partial')
 def test_attrib_owner(self):
  r,c=fixture();a=c['annotations'][0];a.update(type='ATTRIB',parent_path=['B'],owner_insert_identity={'project_id':'P','drawing_ref':'source.dwg','handle':'B','parent_path':[]})
  self.assertEqual(scan(r,[c])['source_references'][0]['owner_insert_identity']['handle'],'B')
 def test_attrib_wrong_owner(self):
  r,c=fixture();c['annotations'][0].update(type='ATTRIB',parent_path=['B'],owner_insert_identity={'handle':'C'});self.assertEqual(scan(r,[c])['source_references'],[])
 def test_table_cell(self):
  r,c=fixture('');i={'project_id':'P','drawing_ref':'source.dwg','snapshot_id':'a'*64,'parent_path':[],'table_handle':'B','row_index':1,'column_index':2}
  c['table_evidence']=[{'provenance':[{'sha256':'a'*64}],'cells':[{'identity':i,'content_kind':'text_observation','text_decode_status':'read','decoded_text':'详见 EW-0073','raw_content':'"详见 EW-0073"'}]}]
  self.assertEqual(scan(r,[c])['source_references'][0]['source_carrier_identity']['column_index'],2)
 def test_mleader_partial(self):
  r,c=fixture();a=c['annotations'][0];a['type']='MLEADER_MTEXT';self.assertEqual(scan(r,[c])['source_references'][0]['reference_extraction_status'],'partial')
 def test_leader_source_only(self):
  r,c=fixture();c['leaders']=[{'type':'LEADER','handle':'L','evidence_version':'1','parent_path':[],'reported_parent_path':'[]','acquisition_scope':'ModelSpace top-level only','reported_scope':'ModelSpace top-level only','source_drawing':'source.dwg','project_id':'P','coordinate_system':'WCS','geometry_status':'read','vertices_wcs':[[0,0,0],[1,1,0]],'vertex_count':2,'arrow_wcs':[0,0,0],'arrow_status':'read','annotation_status':'resolved','annotation_handle':'A','annotation_type':'TEXT','provenance':[{'sha256':'a'*64}]}]
  x=scan(r,[c]);self.assertEqual(len(x['source_references'][0]['source_relations']),1);self.assertEqual(x['resolved_links'],[])
 def field_case(self,code='%<\\AcSm SheetNumber>%'):
  r,c=fixture('');i={'project_id':'P','drawing_ref':'source.dwg','snapshot_id':'a'*64,'handle':'A','parent_path':[]}
  vals={'Handle':'F','Type':'ACAD_FIELD','Status':'read','ChildCount':0,'ReferenceCount':0,'Evaluator':'AcSm','CodeStatus':'read','Code':code}
  raw='FieldGraphVersion="1"\nFieldGraph.Root="F"\nFieldGraph.Status="read"\nFieldNode_BEGIN\n'+''.join('Node.'+k+'='+json.dumps(v)+'\n' for k,v in vals.items())+'FieldNode_END\n'
  c['field_evidence']=[{'carrier_identity':i,'raw_field_record':raw,'provenance':[{'sha256':'a'*64}],'displayed_value':'EW-0073'}];return r,c
 def test_field_graph_required(self):
  r,c=self.field_case();c['field_evidence'][0]['raw_field_record']='';self.assertEqual(scan(r,[c])['source_references'],[])
 def test_field_property_candidate(self):
  r,c=self.field_case();a=scan(r,[c])['source_references'][0];self.assertEqual(a['reference_type'],'field_sheet_reference');self.assertEqual(a['reference_extraction_status'],'partial');self.assertIsNone(a['identifier_raw'])
 def test_field_display_never_identifier(self):
  r,c=self.field_case();self.assertEqual(scan(r,[c])['summary']['references_with_identifier'],0)
 def test_field_wrong_object_type(self):
  r,c=self.field_case();f=c['field_evidence'][0];f['raw_field_record']=f['raw_field_record'].replace('"ACAD_FIELD"','"LINE"');self.assertEqual(scan(r,[c])['source_references'],[])
 def test_heterogeneous_sources(self):
  r,c=fixture();d=drawing('second.dwg','b');d['report_identity']['extractor_version']='2.8-field-graph-evidence-v1';r['drawing_instances'].append(d)
  b=copy.deepcopy(c);b.update(drawing_ref='second.dwg',snapshot_id='b'*64,report_identity=d['report_identity']);b['annotations'][0].update(source_drawing='second.dwg',provenance=[{'sha256':'b'*64}]);self.assertEqual(scan(r,[c,b])['summary']['source_reference_count'],2)
 def test_bad_registry_version(self):
  r,c=fixture();r['registry_version']=True
  with self.assertRaises(ValueError):scan(r,[c])
 def test_filename(self):self.assertEqual(extract_text('详见 EX-plan.dwg')[0]['identifier_raw'],'EX-plan.dwg')
 def test_no_slash_truncation(self):self.assertIsNone(extract_text('详见 E-101/2')[0]['identifier_raw'])
 def test_conflicting_paragraph_span_cannot_hide_conflict(self):
  from mtext_structure import structure_record
  r,c=fixture('详见 EW-0073');a=c['annotations'][0];a['type']='MTEXT';a['mtext_structure']=structure_record(a,c['snapshot_id'])
  b=copy.deepcopy(a);b['decoded_text']='详见 EC-04';b['mtext_structure']=structure_record(b,c['snapshot_id']);c['annotations'].append(b)
  self.assertEqual(len(scan(r,[c])['conflicts']),1)

if __name__=='__main__':unittest.main()
