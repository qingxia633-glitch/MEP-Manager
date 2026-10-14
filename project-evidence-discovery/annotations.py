"""Unicode-safe top-level MEP report adapter. Missing associations stay missing."""
import hashlib,json,re,unicodedata,math
from pathlib import Path
from leader_contract import TOP_LEVEL,validate_leader_evidence_record
from report_manifest import report_identity,verify_manifest
from report_text import serialized_field,text_record
from line_style import style_evidence

def field(text,key):
 m=re.search(r'^'+re.escape(key)+r'=(.*?)\r?$',text,re.M)
 return m[1].strip().strip('"') if m else None
def point(text):
 if text is None:return None
 try:return [float(x) for x in text.strip('()').split()]
 except ValueError:return None
def normalize_text(text):return unicodedata.normalize('NFC',text).replace('\\P','\n').replace('%%p','±').strip()
def corrected_reference(value,object_id,corrections=()):
 if '?' not in value and '\ufffd' not in value:return value,[]
 matches=[c for c in corrections if c.get('historical_value')==value and c.get('status')=='approved'
          and object_id in c.get('target_object_ids',[]) and c.get('provenance')]
 if len(matches)!=1 or '?' in matches[0]['corrected_value'] or '\ufffd' in matches[0]['corrected_value']:
  raise ValueError('Unicode drawing reference requires an approved object-scoped CorrectionEvidence')
 return matches[0]['corrected_value'],[matches[0]['correction_id']]

def categories(text):
 codes=list(dict.fromkeys(re.findall(r'(?<![A-Za-z0-9_+/-])S(?:\s*\+\s*D)?(?![A-Za-z0-9_+/-])',text)))
 codes=[re.sub(r'\s+','',x) for x in codes]
 out=[]
 if codes:out.append('line_code')
 if re.search(r'WDZN[-－]?RYJS|(?<![A-Za-z0-9_])JDG\s*\d+|(?<![A-Za-z0-9_])(?:CC|WC)(?![A-Za-z0-9_])',text,re.I):out.append('specification')
 if re.search(r'余同|其余同|(?<!\w)同(?!\w)',text):out.append('propagation_note')
 if '未注明' in text:out.append('default_rule_text')
 if re.search(r'防火分区|分区编号|局部框选|区域',text):out.append('region_context')
 if re.search(r'报警二总线|火灾报警二总线|报警总线|总线|回路|电源线|系统名称',text):out.append('system_context')
 return out,codes

def load_report(path,project_id=None,encoding='utf-8-sig',manifest=None):
 path=Path(path);data=path.read_bytes();raw=data.decode(encoding)
 verified=verify_manifest(data,path,encoding,manifest) if manifest is not None else None
 drawing=(field(raw,'DWG') or '').replace('\\','/').split('/')[-1]
 if not drawing:raise ValueError('Missing source DWG')
 drawing,_=corrected_reference(drawing,None)
 header=raw.split('EntityHandle=',1)[0]
 top_level=(field(header,'AcquisitionMode')=='ModelSpaceTopLevelAllLayers' and
            field(header,'ModelSpaceTopLevel')=='included' and field(header,'NestedBlocks')=='not expanded')
 measured_hash=hashlib.sha256(data).hexdigest()
 src={'path':str(path),'sha256':measured_hash,'hash_status':'verified' if verified else 'computed_only',
      'encoding':encoding,'report_identity':report_identity(raw),
      'report_integrity':'verified' if verified else 'unavailable/legacy','snapshot_id':measured_hash}
 if verified:src['verified_report_sha256']=verified['report_sha256']
 c={'project_id':project_id,'drawing_ref':drawing,'annotations':[],'unresolved_attributes':[],'targets':[],'leaders':[],
    'report_identity':src['report_identity'],'report_integrity':src['report_integrity'],'snapshot_id':measured_hash,
    'object_associations':[],'bounded_groups':[],'memberships':[],'provenance':[src],'style_evidence':[],
    'extraction_gaps':['nested_blocks_not_expanded','xref_contents_not_expanded','layouts_not_included','proxy_semantics_not_recovered']}
 counts={}
 for rec in re.split(r'(?m)(?=^EntityHandle=)',raw):
  h=field(rec,'EntityHandle');typ=field(rec,'DXF_Type')
  if not h:continue
  counts[typ]=counts.get(typ,0)+1
  provenance=[dict(src,handle=h)];layer=field(rec,'Layer')
  c['style_evidence'].append(style_evidence(rec,header,{'project_id':project_id,'drawing':drawing,
      'snapshot_id':measured_hash,'handle':h,'parent_path':[] if top_level else None},provenance))
  if typ in ('LINE','LWPOLYLINE'):
   vs=[point(x) for x in re.findall(r'^Vertex_WCS=(.*?)\r?$',rec,re.M)]
   if typ=='LINE':vs=[point(field(rec,k)) for k in ('Start_WCS','End_WCS')]
   bulges=[float(v) for v in re.findall(r'Width_or_bulge_DXF=\(42 \. ([^)]+)\)',rec)]
   c['targets'].append({'id':h,'target_type':'edge','layer':layer,'source_drawing':drawing,
      'geometry':{'type':typ,'vertices_wcs':vs,'closed':field(rec,'Closed') not in (None,'nil','false'),
                  'bulges':bulges,'complete':len(vs)>=2 and all(v is not None and len(v)==3 for v in vs)},'provenance':provenance})
  if typ=='INSERT':
   if top_level:
    c['targets'].append({'id':h,'target_type':'device','source_drawing':drawing,'project_id':project_id,'parent_path':[],'provenance':provenance,
                         'note':'INSERT identity only; ModelSpace path established by report acquisition header'})
   else:c['extraction_gaps'].append('insert_parent_scope_not_established:'+h)
   for att in re.split(r'(?m)(?=^AttributeTag=)',rec)[1:]:
    value=field(att,'AttributeText_RAW')
    match=re.search(r'\(5 \. "([^"]+)"\)',field(att,'Attribute_DXF') or '')
    pos=re.search(r'\(10 ([^)]+)\)',field(att,'Attribute_DXF') or '')
    if match and value is not None:
     a={'handle':match[1],'attribute_handle':match[1],'type':'ATTRIB','raw_text':value,'parent_handle':h,
       'parent_path':[h] if top_level else None,'attribute_path':[h,match[1]] if top_level else None,
       'attribute_parent_path':[h] if top_level else None,'owner_insert_handle':h,
       'owner_parent_path':[] if top_level else None,
       'source_drawing':drawing,'project_id':project_id,
       'owner_insert_identity':{'project_id':project_id,'drawing_ref':drawing,'parent_path':[] if top_level else None,'handle':h},
       'association_status':'explicit' if top_level else 'unresolved','position_wcs':point(pos[1]) if pos else None,
       'provenance':[dict(src,handle=match[1],parent_handle=h)],'layer':field(att,'AttributeLayer')}
     c['annotations' if top_level else 'unresolved_attributes'].append(a)
  if typ in ('TEXT','MTEXT','DIMENSION'):
   value=next((field(rec,k) for k in ('Text_RAW','TextString_RAW','Contents_RAW','DimensionText_RAW') if field(rec,k) is not None),None)
   if value is not None:
    key=next(k for k in ('Text_RAW','TextString_RAW','Contents_RAW','DimensionText_RAW') if field(rec,k) is not None)
    c['annotations'].append({'handle':h,'type':typ,'raw_text':value,'layer':layer,
        'parent_path':[] if top_level else None,'source_drawing':drawing,'project_id':project_id,
        **text_record(serialized_field(rec,key)),
        'position_wcs':point(field(rec,'Insertion_WCS')),'bounds':None,'provenance':provenance})
   elif typ=='DIMENSION':c['extraction_gaps'].append('dimension_text_unavailable:'+h)
  if typ in ('LEADER','MLEADER','MULTILEADER'):
   if field(rec,'LeaderEvidenceVersion') is not None:
    version=field(rec,'LeaderEvidenceVersion')
    vs=[point(v) for v in re.findall(r'^LeaderVertex_WCS=(.*?)\r?$',rec,re.M)]
    arrow=point(field(rec,'Arrow_WCS'))
    scope_established=top_level and field(rec,'LeaderScope')==TOP_LEVEL and field(rec,'LeaderParentPath')=='[]'
    count=field(rec,'LeaderVertexCount')
    c['leaders'].append({'handle':h,'type':typ,'evidence_version':version,'parent_path':[] if scope_established else None,
      'reported_parent_path':field(rec,'LeaderParentPath'),'reported_scope':field(rec,'LeaderScope'),
      'acquisition_scope':TOP_LEVEL if top_level else None,'source_drawing':drawing,'project_id':project_id,
      'coordinate_system':field(rec,'LeaderCoordinateSystem'),'geometry_status':field(rec,'LeaderGeometryStatus'),
      'vertex_count':int(count) if count and count.isdecimal() else None,'arrow_status':field(rec,'LeaderArrowStatus'),
      'annotation_status':field(rec,'LeaderAnnotationStatus'),'annotation_type':field(rec,'AnnotationType'),
      'annotation_handle':field(rec,'AnnotationHandle'),'vertices_wcs':vs,'arrow_wcs':arrow,
      'association_status':'unresolved','capability_status':field(rec,'MLeaderCapabilityStatus') or 'not_applicable',
      'raw_record':rec,'provenance':provenance})
    if scope_established and typ in ('MLEADER','MULTILEADER') and field(rec,'MLeaderTextString_Status')=='read':
     value=field(rec,'MLeaderTextString')
     if value is not None:
      content_type=field(rec,'MLeaderContentType')
      c['annotations'].append({'handle':h,'type':'MLEADER_MTEXT' if content_type=='2' else 'MLEADER_CONTENT_UNRESOLVED',
        'content_id':'text_string','reported_content_type':content_type,'owner_entity_handle':h,
        'parent_path':[],'raw_text':value,**text_record(serialized_field(rec,'MLeaderTextString')),
        'position_wcs':None,'layer':layer,'provenance':provenance})
    continue
   # Only explicit exported associations. Runtime object pointers are NOT handles.
   annotation=field(rec,'AnnotationHandle') or field(rec,'TextHandle')
   arrow=point(field(rec,'Arrow_WCS'))
   vs=[point(v) for v in re.findall(r'^LeaderVertex_WCS=(.*?)\r?$',rec,re.M)]
   # Classic LEADER fallback only: raw vertex 10 is WCS; 340 must be a stable handle,
   # not an AutoLISP runtime ename. MLeader nested contexts are not interpreted here.
   if typ=='LEADER':
    if not vs:vs=[point(v) for v in re.findall(r'^Raw_DXF=\(10 ([^)]+)\)\r?$',rec,re.M)]
    ref=re.search(r'^Raw_DXF=\(340 \. "([0-9A-Fa-f]+)"\)\r?$',rec,re.M)
    if not annotation and ref:annotation=ref[1]
    arrow_flag=re.search(r'^Raw_DXF=\(71 \. 1\)\r?$',rec,re.M)
    if arrow is None and arrow_flag and vs:arrow=vs[0]
   c['leaders'].append({'handle':h,'type':typ,'annotation_handle':annotation,'arrow_wcs':arrow,
        'evidence_version':None,'parent_path':[] if top_level else None,
        'reported_parent_path':'[]' if top_level else None,'reported_scope':TOP_LEVEL if top_level else None,
        'acquisition_scope':TOP_LEVEL if top_level else None,'source_drawing':drawing,'project_id':project_id,
        'vertices_wcs':vs,'association_status':'unresolved','provenance':provenance})
 for leader in c['leaders']:
  leader.update(validate_leader_evidence_record(leader,c['annotations'],c))
 c['entity_counts']=counts
 return c
