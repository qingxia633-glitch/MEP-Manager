"""Independent synthetic quantity contract; no project/Golden evidence imported."""
import copy,hashlib,json
def seal(x):
 x['content_hash']=hashlib.sha256(json.dumps({k:v for k,v in x.items() if k!='content_hash'},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();return x
def item():
 b={'project_id':'synthetic-project','drawing_ref':'synthetic.dwg','edge_handle':'synthetic-edge'}
 pv=[{'source_id':'synthetic-review','assertion':'independent synthetic test'}]
 def rec(**kw):return dict(status='supported',binding=copy.deepcopy(b),provenance=copy.deepcopy(pv),**kw)
 transitions=[rec(adjustment_id='entry-'+d,owner=copy.deepcopy(b),device=d,transition_type='box_entry',length=v,unit='m',purpose='design_net') for d,v in [('synthetic-A','0.2'),('synthetic-B','0.3')]]
 na={'status':'not_applicable','reason':'synthetic planar sample','binding':b,'provenance':pv,'items':[]}
 return {'object_id':'synthetic-object','quantity_type_candidate':'conduit',
 'semantic_gate':{'edge_handle':b['edge_handle'],'project_specific_status':'supported','semantic_gate_passed':True,'design_net_quantity_eligible':True,'approved_semantic_role':'synthetic-reviewed-role','provenance':{'context':{'project_id':b['project_id'],'drawing_ref':b['drawing_ref']}}},
 'measurement_scope':rec(kind='edge'),'geometry':rec(base_length='10',source_entity=b['edge_handle'],source_unit='m',engineering_unit='m',conversion=rec(from_unit='m',to_unit='m',factor='1',converted_length='10')),
 'base_path':rec(value='10',unit='m',mode='converted_2d'),'height':{'status':'not_applicable','reason':'synthetic planar sample','binding':b,'provenance':pv},
 'specification':dict(rec(value='synthetic-spec',installation='synthetic-installation',evidence_type='direct_project_binding'),binding_status='supported'),
 'multiplier':rec(value=1,interpretation='one installed route'),
 'adjustments':{'transition':rec(items=transitions,inventory_complete=True,expected_connections=[{'device':e['device'],'transition_type':e['transition_type']} for e in transitions]),'vertical':copy.deepcopy(na),'other':copy.deepcopy(na)},
 'deduplication':rec(key_fields=['edge_handle','segment_id','device','transition_type']),
 'assumptions':[],'verified_sources':{'synthetic-review':{'sha256':'a'*64,'path':'synthetic-evidence.json'}}}
def policy():
 return seal({'policy_id':'synthetic-numeric-policy','scope':{'project_id':'synthetic-project'},'status':'approved','decimal_places':9,'rounding_mode':'ROUND_HALF_EVEN','intermediate_rounding':'none','provenance':[{'source_id':'synthetic-review'}],'is_drawing_fact':False})
def plan(multiplier=1,unit='m'):
 x=item();b=x['measurement_scope']['binding'];records=[x['base_path']]+x['adjustments']['transition']['items']
 vals=['10','0.2','0.3'] if unit=='m' else ['10000','200','300'];terms=[]
 refs=['base_path.value','owned_adjustments/0/length','owned_adjustments/1/length']
 for i,(r,v,ref) in enumerate(zip(records,vals,refs)):
  r['value' if i==0 else 'length']=v;r['unit']=unit
  terms.append({'reference':ref,'original_value':v,'original_unit':unit,'normalized_value':['10','0.2','0.3'][i],'normalized_unit':'m','dimension':'length','conversion':{'source_unit':unit,'target_unit':'m','factor':'1' if unit=='m' else '0.001','status':'approved'},'provenance':r['provenance']})
 x['multiplier']['value']=multiplier;d=x['deduplication'];d.update(evidence_status='supported',execution_status='passed')
 p={'model_type':'QuantityBuildPlan','schema_version':'0.2','object_id':x['object_id'],'quantity_type':'conduit','binding':b,'quantity_eligibility_status':'eligible','quantity_formula_ready':True,'generation_allowed':True,'design_net_quantity_generation_allowed':True,'approved_semantic_role':'synthetic-reviewed-role',
 'base_path':records[0],'owned_adjustments':records[1:],'multiplier':x['multiplier'],'specification':x['specification'],'deduplication':d,'deduplication_status':'passed',
 'formula_components':{'operator':'multiply','arguments':[{'operator':'add','references':refs},'multiplier.value']},
 'unit_execution_contract':{'status':'approved','dimension':'length','target_unit':'m','components':terms,'multiplier':{'original_value':str(multiplier),'original_unit':'dimensionless','normalized_value':str(multiplier),'normalized_unit':'dimensionless','provenance':x['multiplier']['provenance']},'raw_geometry_conversion':x['geometry']['conversion'],'raw_geometry_conversion_usage':'audit_only'},
 'reporting_policy':policy(),'arithmetic_policy':{'numeric_type':'Decimal','precision':80,'intermediate_rounding':'none','inexact_intermediate_action':'reject','rounded_intermediate_action':'reject','final_reporting_policy_ref':'synthetic-numeric-policy'},'assumptions':[],'provenance':x['verified_sources'],'source_evidence_hashes':copy.deepcopy(x['verified_sources']),'source_build_plan_hash':'b'*64,'source_decision_artifact_hash':'c'*64,'corrections_applied':{}}
 return seal(p)
