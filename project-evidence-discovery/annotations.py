"""Unicode-safe top-level MEP report adapter. Missing associations stay missing."""
import hashlib,json,re,unicodedata
from pathlib import Path

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

def load_report(path,project_id=None):
 path=Path(path);data=path.read_bytes();raw=data.decode('utf-8-sig')
 drawing=(field(raw,'DWG') or '').replace('\\','/').split('/')[-1]
 if not drawing:raise ValueError('Missing source DWG')
 drawing,_=corrected_reference(drawing,None)
 src={'path':str(path),'sha256':hashlib.sha256(data).hexdigest()}
 c={'project_id':project_id,'drawing_ref':drawing,'annotations':[],'targets':[],'leaders':[],
    'object_associations':[],'bounded_groups':[],'memberships':[],'provenance':[src],
    'extraction_gaps':['nested_blocks_not_expanded','xref_contents_not_expanded','layouts_not_included','proxy_semantics_not_recovered']}
 counts={}
 for rec in re.split(r'(?m)(?=^EntityHandle=)',raw):
  h=field(rec,'EntityHandle');typ=field(rec,'DXF_Type')
  if not h:continue
  counts[typ]=counts.get(typ,0)+1
  provenance=[dict(src,handle=h)];layer=field(rec,'Layer')
  if typ in ('LINE','LWPOLYLINE'):
   vs=[point(x) for x in re.findall(r'^Vertex_WCS=(.*?)\r?$',rec,re.M)]
   if typ=='LINE':vs=[point(field(rec,k)) for k in ('Start_WCS','End_WCS')]
   bulges=[float(v) for v in re.findall(r'Width_or_bulge_DXF=\(42 \. ([^)]+)\)',rec)]
   c['targets'].append({'id':h,'target_type':'edge','layer':layer,'source_drawing':drawing,
      'geometry':{'type':typ,'vertices_wcs':vs,'closed':field(rec,'Closed') not in (None,'nil','false'),
                  'bulges':bulges,'complete':len(vs)>=2 and all(v is not None and len(v)==3 for v in vs)},'provenance':provenance})
  if typ=='INSERT':
   c['targets'].append({'id':h,'target_type':'device','source_drawing':drawing,'project_id':project_id,'parent_path':[],'provenance':provenance,
                        'note':'INSERT identity only; no electrical device role inferred'})
   for att in re.split(r'(?m)(?=^AttributeTag=)',rec)[1:]:
    value=field(att,'AttributeText_RAW')
    match=re.search(r'\(5 \. "([^"]+)"\)',field(att,'Attribute_DXF') or '')
    pos=re.search(r'\(10 ([^)]+)\)',field(att,'Attribute_DXF') or '')
    if match and value is not None:
     c['annotations'].append({'handle':match[1],'type':'ATTRIB','raw_text':value,'parent_handle':h,
       'parent_path':[h],'attribute_path':[h,match[1]],'owner_parent_path':[],
       'source_drawing':drawing,'project_id':project_id,
       'owner_insert_identity':{'project_id':project_id,'drawing_ref':drawing,'parent_path':[],'handle':h},
       'association_status':'explicit','position_wcs':point(pos[1]) if pos else None,
       'provenance':[dict(src,handle=match[1],parent_handle=h)],'layer':field(att,'AttributeLayer')})
  if typ in ('TEXT','MTEXT','DIMENSION'):
   value=next((field(rec,k) for k in ('Text_RAW','TextString_RAW','Contents_RAW','DimensionText_RAW') if field(rec,k) is not None),None)
   if value is not None:
    c['annotations'].append({'handle':h,'type':typ,'raw_text':value,'layer':layer,
        'position_wcs':point(field(rec,'Insertion_WCS')),'bounds':None,'provenance':provenance})
   elif typ=='DIMENSION':c['extraction_gaps'].append('dimension_text_unavailable:'+h)
  if typ in ('LEADER','MLEADER','MULTILEADER'):
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
        'vertices_wcs':vs,'association_status':'explicit' if annotation else 'unresolved','provenance':provenance})
 c['entity_counts']=counts
 return c
