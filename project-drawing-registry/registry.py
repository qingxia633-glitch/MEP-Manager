"""Acquisition-instance directory. No engineering interpretation or approval."""
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'project-evidence-discovery'))
from annotations import load_report
from report_manifest import verify_manifest, report_identity

VERSIONS = {'2.3-text-layout-metadata','2.4-leader-evidence-v1',
 '2.5-line-style-evidence-v1','2.6-table-cell-evidence-v1',
 '2.7-field-provenance-v1','2.8-field-graph-evidence-v1'}
END = 'END_OF_REPORT: scan finished. Inspect errors and scope limitations before interpreting results.'

def content_hash(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()

def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def required(value,name):
 if not isinstance(value,str) or not value.strip():raise ValueError('missing '+name)
 return value

def key(value):return unicodedata.normalize('NFC',value).casefold().strip()

def observe(project,item):
 path=Path(item['report_path']);data=path.read_bytes()
 manifest_path=item.get('manifest_path');manifest=None
 if manifest_path:manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
 encoding=manifest['encoding'] if manifest is not None else required(item.get('encoding'),'encoding')
 raw=data.decode(encoding);identity=report_identity(raw);header=raw.split('EntityHandle=',1)[0]
 def header_value(name):
  hits=re.findall(r'^'+re.escape(name)+r'=(.*?)\r?$',header,re.M)
  if len(hits)>1:raise ValueError('duplicate header '+name)
  return hits[0].strip().strip('"') if hits else None
 drawing=required(header_value('DWG'),'drawing_ref')
 version=header_value('ExtractorVersion')
 if version not in VERSIONS:raise ValueError('unsupported report version')
 for name in ('AcquisitionMode','ModelSpaceTopLevel','NestedBlocks','AllLayers','XrefContents','PaperSpaceLayouts'):header_value(name)
 if not raw.rstrip().endswith(END) or re.findall(r'^ReadErrorCount=(.*?)\r?$',raw,re.M)!=['0']:
  raise ValueError('incomplete or error-bearing report')
 integrity='computed_only'
 if manifest is not None:
  verify_manifest(data,path,encoding,manifest);integrity='verified'
 report_hash=hashlib.sha256(data).hexdigest()
 source_hash=item.get('source_dwg_sha256');hash_status='unavailable'
 if source_hash is not None:
  if not isinstance(source_hash,str) or not re.fullmatch('[0-9a-f]{64}',source_hash):raise ValueError('invalid DWG hash')
  hash_status='declared_unverified'
 if item.get('source_dwg_path'):
  actual=file_hash(item['source_dwg_path'])
  if source_hash is not None and actual!=source_hash:raise ValueError('DWG hash mismatch')
  source_hash=actual;hash_status='verified'
 basis={'project_id':project,'drawing_ref':drawing,'source_dwg_sha256':source_hash,'report_sha256':report_hash}
 iid=content_hash(basis)
 provenance=[{'source_type':'report_bytes','sha256':report_hash,'report_identity':identity,
              'integrity':integrity,'project_assignment':'explicit input; not independently authenticated'}]
 if manifest is not None:provenance.append({'source_type':'manifest_v2','sha256':file_hash(manifest_path)})
 if source_hash:provenance.append({'source_type':'source_dwg_bytes','sha256':source_hash,'status':hash_status})
 scope={n:header_value(n) for n in ('AcquisitionMode','ModelSpaceTopLevel','NestedBlocks','AllLayers','XrefContents','PaperSpaceLayouts')}
 model='acquired' if scope['AcquisitionMode']=='ModelSpaceTopLevelAllLayers' and scope['ModelSpaceTopLevel']=='included' else 'unresolved'
 basename=PureWindowsPath(drawing).name
 aliases=[]
 def alias(kind,value,source,source_identity,status='partial'):
  aliases.append({'kind':kind,'value':value,'source_type':source,'source_identity':source_identity,
                  'status':status,'provenance':provenance,'instance_id':iid,
                  'identifies_current_drawing':'observed_source_name' if source=='report_header' else 'unresolved'})
 alias('source_filename',basename,'report_header',identity,'observed')
 alias('filename_stem',PureWindowsPath(basename).stem,'report_header',identity,'candidate')
 context=load_report(path,project_id=project,encoding=encoding,manifest=manifest)
 observations=[]
 for a in context['annotations']:
  src={'project_id':project,'drawing_ref':drawing,'snapshot_id':report_hash,'handle':a['handle'],'parent_path':a.get('parent_path')}
  observations.append((a.get('decoded_text'),a['type'],src))
  if a['type']=='ATTRIB' and a.get('tag') in ('图号','图名','图纸名称','Drawing No.','Sheet No.') and a.get('text_decode_status')=='read':
   observations.append((a['tag']+':'+a['decoded_text'],'ATTRIB_tag_value',dict(src,tag=a['tag'],owner=a.get('owner_insert_identity'))))
 for table in context['table_evidence']:
  for cell in table['cells']:observations.append((cell.get('decoded_text'),'TABLE_'+cell['content_kind'],cell['identity']))
 # Same-record explicit key/value only. Never combine adjacent text or cells.
 pattern=r'^\s*(图号|图名|图纸名称|Drawing No\.|Sheet No\.)\s*[:：]\s*([^\r\n]+)\s*$'
 for text,typ,src in observations:
  match=re.fullmatch(pattern,text or '',re.I)
  if match:
   label,value=match.groups()
   kind='drawing_title_candidate' if label in ('图名','图纸名称') else 'sheet_number_candidate' if label.lower()=='sheet no.' else 'drawing_number_candidate'
   alias(kind,value,typ,src)
 if path.read_bytes()!=data:raise ValueError('report changed during read')
 if manifest_path and json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))!=manifest:raise ValueError('manifest changed during read')
 return dict(basis,instance_id=iid,source_filename=basename,source_path_status='observed_reference_not_authoritative',
  source_dwg_hash_status=hash_status,report_version=version,report_identity=identity,report_integrity=integrity,
  acquisition_scope=scope,snapshot_id=report_hash,modelspace_status=model,
  layout_status='unresolved_out_of_scope',layout_inventory_status='unresolved',paperspace_acquisition_status='not_established',
  spaces=[{'type':'ModelSpace','acquisition_status':model}],logical_identity_status='unresolved',sheet_identity_status='unresolved',
  drawing_number_status='unresolved',revision_evidence={'source_content_hash':source_hash,'report_snapshot':report_hash,'formal_revision_identity':None,'status':'unresolved'},
  labels=sorted(aliases,key=content_hash),provenance=provenance,registry_status='supported' if integrity=='verified' and model=='acquired' else 'partial')

def build_registry(project_id,inputs):
 required(project_id,'project_id')
 if not isinstance(inputs,list) or not inputs:raise ValueError('inputs must be nonempty list')
 instances={}
 for item in inputs:
  d=observe(project_id,item);iid=d['instance_id']
  if item.get('layout_report_path'):
   sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'drawing-sheet-identity'))
   from identity import read_identity
   evidence=read_identity(d,item['layout_report_path'],required(item.get('layout_report_sha256'),'layout_report_sha256'))
   d['drawing_sheet_identity_evidence']=evidence
   d['layout_inventory']=evidence['layouts']
   d['layout_status']='acquired'
   d['layout_inventory_status']='read'
   d['paperspace_acquisition_status']='read' if all(x['layout_acquisition_status']=='read' for x in evidence['layouts']) else 'partial'
   d['logical_identity_status']=evidence['identity_status']
   d['sheet_identity_status']=evidence['sheet_identity_status']
   # Preserve every role in identity evidence. The unchanged cross-sheet v1
   # consumer only accepts its established alias kinds, never revision/title guesses.
   compatible={'drawing_number_candidate','sheet_number_candidate','drawing_title_candidate'}
   for c in evidence['candidates']:
    if evidence['identity_status']=='candidate' and c['kind'] in compatible:
     attachment={'project_id':project_id,'snapshot_id':d['report_sha256'],
                 'drawing_instance_id':iid,'layout_evidence_sha256':item['layout_report_sha256'],
                 'identity_kind':'registry_acquisition_attachment; actual carrier retained separately'}
     d['labels'].append(dict(c,instance_id=iid,source_type='layout_title_block',
                           source_identity=attachment,provenance=d['provenance']+c['provenance']))
   d['labels']=sorted(d['labels'],key=content_hash)
  if iid in instances and instances[iid]!=d:raise ValueError('same instance has conflicting metadata')
  instances[iid]=d
 drawings=[instances[k] for k in sorted(instances)]
 aliases=sorted([a for d in drawings for a in d['labels']],key=content_hash)
 index={}
 for a in aliases:index.setdefault(key(a['value']),set()).add(a['instance_id'])
 ambiguities=[{'alias':k,'instance_ids':sorted(v),'status':'ambiguous'} for k,v in sorted(index.items()) if len(v)>1]
 return {'registry_version':1,'project_id':project_id,'drawing_instances':drawings,'aliases':aliases,
  'lookup_index':{k:sorted(v) for k,v in sorted(index.items())},'ambiguities':ambiguities,'conflicts':[],
  'unresolved':[{'instance_id':d['instance_id'],'logical_identity':d['logical_identity_status'],'sheet_identity':d['sheet_identity_status'],'formal_revision':'unresolved'} for d in drawings],
  'provenance':[{'instance_id':d['instance_id'],'sources':d['provenance']} for d in drawings],
  'summary':{'drawing_instance_count':len(drawings),'supported_instance_count':sum(d['registry_status']=='supported' for d in drawings),
    'ambiguous_identity_count':len(ambiguities),'unresolved_logical_identity_count':sum(d['logical_identity_status']=='unresolved' for d in drawings),
    'layout_coverage':'layout_evidence_present' if any('layout_inventory' in d for d in drawings) else 'unresolved_out_of_scope','report_version_distribution':dict(sorted(Counter(d['report_version'] for d in drawings).items()))}}

def lookup(registry,value,kind=None):
 required(value,'lookup value')
 ids=sorted({a['instance_id'] for a in registry['aliases'] if key(a['value'])==key(value) and (kind is None or a['kind']==kind)})
 return {'lookup_status':'not_found' if not ids else 'matched' if len(ids)==1 else 'ambiguous','matches':ids,'match_count':len(ids),
         'logical_identity_approved':False,'match_evidence':[a for a in registry['aliases'] if key(a['value'])==key(value) and (kind is None or a['kind']==kind)]}
