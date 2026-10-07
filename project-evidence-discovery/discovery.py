"""Discover traceable candidates only. No project semantics, approval, or quantity."""
from copy import deepcopy
import math
from annotations import categories,normalize_text,corrected_reference
from bindings import nearest,valid_point
from model import identity,EXPORTER_FIELDS

def discover(context,xy_tolerance=.001,nearby_distance=1000):
 if not math.isfinite(xy_tolerance) or xy_tolerance<=0 or not math.isfinite(nearby_distance) or nearby_distance<0:
  raise ValueError('Finite positive connection tolerance and nonnegative context radius required')
 drawing,_=corrected_reference(context['drawing_ref'],None)
 targets=[t for t in context.get('targets',[]) if t.get('source_drawing',drawing)==drawing]
 byid={t['id']:t for t in targets}
 evidence=[];bindings=[];roots=[];members=[];seen={}
 for a in context.get('annotations',[]):
  if a.get('source_drawing',drawing)!=drawing:continue
  raw=a.get('raw_text','');normalized=normalize_text(raw);cats,codes=categories(normalized)
  if not cats:continue
  key=(a['handle'],a.get('parent_path',[]).__repr__())
  if key in seen:
   if seen[key]['raw_text']!=raw:
    seen[key]['binding_status']='conflicting';seen[key]['discovery_gaps'].append('conflicting_annotation_content')
   continue
  eid=identity(drawing,a['handle'],a.get('parent_path',[]),raw)
  e={'object_type':'EvidenceCandidate','evidence_id':eid,'source_drawing':drawing,'source_handle':a['handle'],
     'source_layer':a.get('layer'),
     'source_entity_type':a['type'],'raw_text':raw,'normalized_text':normalized,'evidence_category':cats,
     'line_codes':codes,'coordinate_wcs':a.get('position_wcs'),'bounds':a.get('bounds'),
     'parent_path':a.get('parent_path',[]),'binding_method':'unbound_text','binding_status':'unresolved',
     'text_relation':'text_exists','target_candidates':[],'leader_geometry':[],'anchor_geometry':[],
     'scope_candidate':None,'propagation_candidate':None,'exclusions':[],
     'provenance':deepcopy(a.get('provenance',context.get('provenance',[]))),
     'assumptions':['XY contact does not establish electrical function','Nearby text is not binding',
                    'No specification-to-S inference; no unbounded propagation'],
     'discovery_gaps':[],'discovery_status':'unresolved'}
  seen[key]=e;evidence.append(e)
  near=[]
  for t in targets:
   n=nearest(a.get('position_wcs'),t)
   if n and n['distance']<=nearby_distance:
    near.append({'target_id':t['id'],'target_type':t['target_type'],'relation':'text_near_edge',**n})
  e['target_candidates']=sorted(near,key=lambda x:(x['distance'],x['target_id']))
  if near:e.update(binding_method='nearby_context',text_relation='text_near_edge')
  hits=[]
  # Attribute ownership is an object association, never a nearby edge association.
  if a.get('type')=='ATTRIB' and a.get('association_status')=='explicit' and a.get('parent_handle') in byid and a.get('provenance'):
   hits.append((byid[a['parent_handle']],None,'direct_object_binding',{'attribute_owner':a['parent_handle']}))
  for assoc in context.get('object_associations',[]):
   if (assoc.get('annotation_handle')==a['handle'] and assoc.get('status')=='supported' and assoc.get('provenance') and
       assoc.get('source_drawing',drawing)==drawing and assoc.get('target_id') in byid):
    hits.append((byid[assoc['target_id']],None,'direct_object_binding',deepcopy(assoc)))
  leaders=[l for l in context.get('leaders',[]) if l.get('annotation_handle')==a['handle'] and l.get('source_drawing',drawing)==drawing]
  e['leader_geometry']=deepcopy(leaders)
  for l in leaders:
   vertices=l.get('vertices_wcs',[])
   if (l.get('association_status')!='explicit' or not l.get('provenance') or not valid_point(l.get('arrow_wcs')) or
       not vertices or not all(valid_point(v) for v in vertices) or
       not any(math.dist(l['arrow_wcs'],v)<=xy_tolerance for v in vertices)):
    e['discovery_gaps'].append('leader_geometry_unavailable');continue
   for t in targets:
    n=nearest(l['arrow_wcs'],t)
    if n and n['distance']<=xy_tolerance:hits.append((t,n,'leader_binding',{'leader':l['handle'],'arrow_wcs':l['arrow_wcs']}))
  unique={ (t['id'],method,str(basis)): (t,n,method,basis) for t,n,method,basis in hits }
  hits=list(unique.values());hit_ids={t['id'] for t,_,_,_ in hits}
  for t,n,method,basis in hits:
   status='supported' if len(hit_ids)==1 else 'partial'
   b={'object_type':'EvidenceBindingCandidate','binding_id':identity(eid,t['id'],method,basis),
      'evidence_id':eid,'source_drawing':drawing,'annotation_handle':a['handle'],
      'target_id':t['id'],'target_type':t['target_type'],'binding_method':method,'binding_status':status,
      'relation':'leader_points_to_edge' if method=='leader_binding' else 'text_attached_to_object',
      'distance':n['distance'] if n else None,'geometric_basis':n or basis,'line_codes':codes,
      'z_semantics':'unresolved','xy_tolerance':xy_tolerance,'provenance':deepcopy(e['provenance'])+[basis]}
   bindings.append(b);e['target_candidates'].append(deepcopy(b));e['anchor_geometry'].append(basis)
  if hits:
   e.update(binding_method=hits[0][2],binding_status='supported' if len(hit_ids)==1 else 'partial',
            text_relation='leader_points_to_edge' if hits[0][2]=='leader_binding' else 'text_attached_to_object',
            discovery_status='supported' if len(hit_ids)==1 else 'partial')
  else:
   e['discovery_gaps'].append('leader_geometry_unavailable' if not leaders else 'target_binding_not_established')
  if 'propagation_note' in cats:
   root=next(iter(hit_ids)) if len(hit_ids)==1 else None
   groups=[g for g in context.get('bounded_groups',[]) if root and g.get('annotation_handle')==a['handle'] and
      g.get('root_target_id')==root and g.get('source_drawing',drawing)==drawing and g.get('status')=='supported' and g.get('provenance')]
   valid=[g for g in groups if isinstance(g.get('bounded_set'),list) and all(g.get(k) for k in ('propagation_relation','scope_boundary','termination_condition'))]
   scope_status='supported' if len(valid)==1 else 'unresolved'
   p={'object_type':'PropagationRootCandidate','annotation_handle':a['handle'],'raw_text':raw,
      'root_target_candidate':root,'root_target_type':byid[root]['target_type'] if root else None,
      'root_status':'supported' if root else 'unresolved','propagation_scope_status':scope_status,
      'leader_root_geometry':deepcopy(e['anchor_geometry']),
      'propagation_relation_candidate':valid[0]['propagation_relation'] if scope_status=='supported' else None,
      'scope_boundary_candidate':valid[0]['scope_boundary'] if scope_status=='supported' else None,
      'termination_candidate':valid[0]['termination_condition'] if scope_status=='supported' else None,
      'bounded_set':valid[0]['bounded_set'] if scope_status=='supported' else [],'global_propagation':False,
      'provenance':deepcopy(e['provenance'])+deepcopy(valid)}
   roots.append(p);e['propagation_candidate']=p
   if not root:e['discovery_gaps'].append('root_target_unknown')
   elif scope_status!='supported':e['discovery_gaps'].append('propagation_boundary_unknown');e['discovery_status']='partial'
   else:e['scope_candidate']=deepcopy(valid[0]);e['binding_method']='bounded_group_binding'
  if 'region_context' in cats or 'system_context' in cats:
   e['scope_candidate']=e['scope_candidate'] or {'status':'unresolved','text':raw,'membership_not_established':True}
   e['discovery_gaps'].append('region_or_system_scope_not_established')
  for m in context.get('memberships',[]):
   if m.get('annotation_handle')!=a['handle'] or not m.get('provenance') or not m.get('geometric_basis') or m.get('source_drawing',drawing)!=drawing:continue
   kind=m.get('target_type')
   if kind not in ('device','edge','annotation'):continue
   members.append({'object_type':'EvidenceBindingCandidate','binding_method':'region_membership_candidate',
     'binding_status':'partial','target_id':m['target_id'],'target_type':kind,
     'relation':'system_membership_candidate' if m.get('membership_kind')=='system' else kind+'_in_region',
     'region_id':m.get('region_id'),'geometric_basis':deepcopy(m['geometric_basis']),'provenance':deepcopy(m['provenance'])})
 # Conflicting source annotations cannot leave earlier positive bindings behind.
 conflicts={e['evidence_id'] for e in evidence if e['binding_status']=='conflicting'}
 for b in bindings:
  if b['evidence_id'] in conflicts:b['binding_status']='conflicting'
 for e in evidence:
  if not valid_point(e['coordinate_wcs']):e['discovery_gaps'].append('annotation_wcs_unavailable')
  if e['binding_status']=='conflicting':
   for candidate in e['target_candidates']:
    if candidate.get('evidence_id')==e['evidence_id']:candidate['binding_status']='conflicting'
   e['discovery_status']='unresolved'
  e['evidence_strength']=e['binding_method']
  e['leader_availability']='available' if e['leader_geometry'] and 'leader_geometry_unavailable' not in e['discovery_gaps'] else 'unavailable'
  e['text_scope_status']='text_scope_unknown' if e['binding_status']!='supported' else 'candidate_target_only'
  e['discovery_gaps']=list(dict.fromkeys(e['discovery_gaps']))
  if e['binding_status']=='conflicting' and e['propagation_candidate']:
   e['propagation_candidate'].update(root_status='conflicting',propagation_scope_status='unresolved',bounded_set=[])
 for b in bindings:b['evidence_strength']=b['binding_method']
 summaries={}
 for t in targets:
  if t['target_type']!='edge':continue
  bs=[b for b in bindings if b['target_id']==t['id']]
  strong=[b for b in bs if b['binding_status']=='supported']
  related=[e for e in evidence if any(x['target_id']==t['id'] for x in e['target_candidates'])]
  codes=set(code for b in bs for code in b['line_codes'])
  summaries[t['id']]={'direct_binding_count':len(strong),'bounded_rule_candidate_count':sum(
     p['propagation_scope_status']=='supported' and {'target_id':t['id'],'target_type':'edge'} in p['bounded_set'] for p in roots),
     'unresolved_binding_count':sum(e['binding_status']!='supported' for e in related),
     'specification_binding_candidate':any('specification' in e['evidence_category'] and any(b['evidence_id']==e['evidence_id'] for b in strong) for e in evidence),
     'system_binding_candidate':any('system_context' in e['evidence_category'] and any(b['evidence_id']==e['evidence_id'] for b in strong) for e in evidence),
     'selection_status':'conflicting' if len(codes)>1 else ('candidate' if codes and strong else 'unresolved'),
     'line_code_candidates':sorted(codes),'nearby_evidence_ids':[e['evidence_id'] for e in related]}
 return {'object_type':'ProjectEvidenceDiscoveryResult','version':'0.1','source_drawing':drawing,
    'evidence':evidence,'bindings':bindings,'propagation_roots':roots,'membership_candidates':members,
    'edge_summaries':summaries,'xy_tolerance':xy_tolerance,'nearby_distance':nearby_distance,
    'exporter_fields_needed':EXPORTER_FIELDS,'extraction_gaps':context.get('extraction_gaps',[]),
    'unsupported_curved_target_ids':[t['id'] for t in targets if any(t.get('geometry',{}).get('bulges',[]))],
    'provenance':deepcopy(context.get('provenance',[]))}
