"""Layout-qualified identity candidates, never sheet or engineering approval."""
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'project-evidence-discovery'))
from report_text import decode_exported_string
from field_graph import graph_record

VERSION = 1
REPORT_VERSION = '2.9-layout-identity-v1'
ROLES = {
    '图号':'drawing_number', 'DRAWING NO':'drawing_number', 'DWG NO':'drawing_number',
    'SHEET NO':'sheet_number', 'SHEET NUMBER':'sheet_number',
    '图名':'drawing_title', '图纸名称':'drawing_title', 'DRAWING TITLE':'drawing_title',
    'SHEET TITLE':'sheet_title', 'TITLE':'unresolved_title', 'NO':'unresolved_number',
    'NUMBER':'unresolved_number', 'REV':'revision_number', 'REVISION':'revision_number',
    '修订号':'revision_number', '版本':'revision_number', 'REVISION DATE':'revision_date', '修订日期':'revision_date',
    'REVISION DESCRIPTION':'revision_description', 'REVISION PURPOSE':'revision_description',
    '修订说明':'revision_description',
}
FIELD_ROLES = {'SheetNumber':'sheet_number', 'SheetTitle':'sheet_title',
               'RevisionNumber':'revision_number', 'RevisionDate':'revision_date'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False).encode()).hexdigest()


def scalar(raw, key, optional=False):
    hits = re.findall(r'^'+re.escape(key)+r'=(.*?)\r?$', raw, re.M)
    if optional and not hits:return None
    if len(hits)!=1:raise ValueError('missing or duplicate '+key)
    value=hits[0]
    if value.startswith('"'):return decode_exported_string(value)
    if re.fullmatch(r'\d+',value):return int(value)
    if value=='nil' and optional:return None
    raise ValueError('invalid scalar '+key)


def blocks(raw, name):
    result=re.findall(r'^'+name+r'_BEGIN\r?\n(.*?)^'+name+r'_END\r?$',raw,re.M|re.S)
    for suffix in ('BEGIN','END'):
        if len(re.findall(r'^'+name+'_'+suffix+r'\r?$',raw,re.M))!=len(result):
            raise ValueError('incomplete '+name+' envelope')
    return result


def dxf_string(raw, code):
    hits=re.findall(r'\('+str(code)+r' \. ("(?:\\.|[^"\\])*")\)',raw)
    return decode_exported_string(hits[0]) if len(hits)==1 else None


def role(tag):return ROLES.get(re.sub(r'[_.\s]+',' ',tag.upper()).strip())


def read_identity(instance, path, expected_hash):
    data=Path(path).read_bytes();sha=hashlib.sha256(data).hexdigest()
    if sha!=expected_hash:raise ValueError('layout report hash mismatch')
    if instance.get('source_dwg_hash_status')!='verified':raise ValueError('verified source DWG required')
    raw=data.decode('utf-8-sig')
    if not raw.rstrip().endswith('END_LAYOUT_REPORT'):raise ValueError('incomplete layout report')
    header=raw.split('Layout_BEGIN',1)[0]
    if scalar(header,'ReportVersion')!=REPORT_VERSION or scalar(header,'DrawingSheetIdentityEvidenceVersion')!='1':raise ValueError('unsupported layout contract')
    if scalar(header,'LayoutOwnerContractVersion')!='1' or scalar(header,'OwnerExtractionSelfTest')!='PASS':raise ValueError('owner extraction contract unavailable')
    drawing_literal=re.findall(r'^DWG=(.*?)\r?$',header,re.M)
    if scalar(header,'DWG')!=instance['drawing_ref'] and drawing_literal[0][1:-1]!=instance['drawing_ref']:raise ValueError('foreign drawing reference')
    if scalar(header,'LayoutInventoryStatus')!='read':raise ValueError('layout inventory unavailable')
    records=blocks(raw,'Layout')
    if scalar(raw,'LayoutCount')!=len(records):raise ValueError('layout count mismatch')
    provenance=[{'source_type':'layout_report_bytes','path':str(path),'sha256':sha,'report_version':REPORT_VERSION}]
    result={'DrawingSheetIdentityEvidenceVersion':VERSION,'report_version':REPORT_VERSION,
            'project_id':instance['project_id'],'drawing_instance_id':instance['instance_id'],
            'layouts':[],'title_blocks':[],'candidates':[],'sheet_candidates':[],
            'paper_entity_inventory':[],'field_observations':[],
            'sheet_set_evidence':{'status':'unavailable','reason':'no independent Sheet Set acquisition in this contract'},
            'identity_status':'unresolved','sheet_identity_status':'unresolved','provenance':provenance}
    seen_layouts=set();seen_names=set();seen_blocks=set();seen_entities=set()
    for record in records:
        meta=record.split('PaperEntity_BEGIN',1)[0]
        name=scalar(meta,'LayoutName');handle=scalar(meta,'LayoutHandle');block=scalar(meta,'SpaceBlockHandle')
        space=scalar(meta,'SpaceType')
        if not name or not re.fullmatch('[0-9A-Fa-f]+',handle) or not re.fullmatch('[0-9A-Fa-f]+',block):raise ValueError('invalid layout identity')
        if handle in seen_layouts or name in seen_names or block in seen_blocks:raise ValueError('duplicate layout identity')
        seen_layouts.add(handle);seen_names.add(name);seen_blocks.add(block)
        if space not in ('ModelSpace','PaperSpace'):raise ValueError('unknown space')
        lid=digest([instance['project_id'],instance['instance_id'],name,handle,block])
        entities=blocks(record,'PaperEntity')
        if scalar(record,'LayoutEntityCount')!=len(entities):raise ValueError('entity count mismatch')
        if space=='ModelSpace' and entities:raise ValueError('ModelSpace entities mixed into layout report')
        available=scalar(meta,'LayoutAcquisitionStatus')=='read' and scalar(record,'LayoutReadErrorCount')==0
        l={'project_id':instance['project_id'],'drawing_instance_id':instance['instance_id'],
           'layout_name':name,'layout_identity':lid,'layout_source_identity':{'handle':handle,'block_handle':block},
           'space_type':space,'model_or_paper_space':space,'layout_order':scalar(meta,'LayoutOrder',True),
           'layout_acquisition_status':'read' if available else 'unavailable',
           'entity_scope':'inventory_only' if space=='ModelSpace' else 'top_level_with_attached_attributes',
           'entity_count':len(entities),'parent_path_rules':'[] for space top-level; [INSERT handle] for attached ATTRIB',
           'provenance':provenance}
        result['layouts'].append(l)
        for entity in entities:
            head=entity.split('AttributeTag=',1)[0]
            eh=scalar(head,'EntityHandle');typ=scalar(head,'DXF_Type')
            if not isinstance(eh,str) or not re.fullmatch('[0-9A-Fa-f]+',eh) or eh in seen_entities:raise ValueError('duplicate or invalid entity identity')
            seen_entities.add(eh)
            if scalar(head,'EntityLayoutName')!=name or scalar(head,'EntityOwnerBlock')!=block or scalar(head,'EntityOwnerType')!='BLOCK_RECORD':raise ValueError('entity space mismatch')
            base={'project_id':instance['project_id'],'drawing_instance_id':instance['instance_id'],
                  'drawing_ref':instance['drawing_ref'],'snapshot_id':sha,'layout_identity':lid,'handle':eh,'parent_path':[]}
            result['paper_entity_inventory'].append({'identity':base,'entity_type':typ,
                'raw_record_sha256':hashlib.sha256(entity.encode('utf-8')).hexdigest(),
                'provenance':provenance,'membership_status':'native_layout_block_and_owner_verified'})
            if typ in ('TEXT','MTEXT'):
                for f in blocks(entity,'FieldEvidence'):
                    if scalar(f,'Field.CarrierHandle',True)==eh:
                        result['field_observations'].append({'carrier_identity':base,
                          'display_value':scalar(entity,'Text_RAW',True),'field_graph':graph_record(f,base,provenance),
                          'title_block_membership':'unresolved','provenance':provenance})
            if typ!='INSERT':continue
            attrs=[];defaults=[];attr_ids=set()
            for a in re.split(r'^AttributeTag=',entity,flags=re.M)[1:]:
                a='AttributeTag='+a
                # The last attribute may be followed by block definition records.
                a=a.split('ConstantAttributeDefinition_BLOCK_LOCAL=',1)[0].split('DynamicMetadata_BEGIN',1)[0]
                tag=scalar(a,'AttributeTag');value=scalar(a,'AttributeText_RAW')
                dx=re.findall(r'^Attribute_DXF=(.*?)\r?$',a,re.M)
                ah=dxf_string(dx[0],5) if len(dx)==1 else None
                if not ah or ah in attr_ids or ah in seen_entities:raise ValueError('invalid/duplicate attribute identity')
                if scalar(a,'AttributeLayout.ParentINSERTHandle')!=eh:raise ValueError('attribute owner mismatch')
                attr_ids.add(ah);seen_entities.add(ah)
                carrier=dict(base,handle=ah,parent_path=[eh],owner_insert_handle=eh)
                graphs=[]
                for f in blocks(a,'FieldEvidence'):
                    if scalar(f,'Field.CarrierHandle',True)==ah and scalar(f,'FieldEvidenceVersion',True)=='2':graphs.append(graph_record(f,carrier,provenance))
                attrs.append({'tag':tag,'raw_value':value,'displayed_value':value,'carrier_identity':carrier,
                              'source_status':'instance_ATTRIB','field_graphs':graphs,'provenance':provenance})
                for g in graphs:
                    if g['nodes']:result['field_observations'].append({'carrier_identity':carrier,'display_value':value,
                        'field_graph':g,'title_block_membership':'owner_INSERT_observed','provenance':provenance})
            for d in re.findall(r'^ConstantAttributeDefinition_BLOCK_LOCAL=(.*?)\r?$',entity,re.M):
                defaults.append({'tag':dxf_string(d,2),'value':dxf_string(d,1),'handle':dxf_string(d,5),
                                 'source_status':'definition_default_only','raw_dxf':d,'provenance':provenance})
            metadata={role(a['tag']) for a in attrs} - {None}
            if not available or len(metadata)<2 or not any(x.endswith(('number','title')) and not x.startswith('revision') for x in metadata):continue
            tid=digest([instance['instance_id'],lid,[],eh])
            tb={'title_block_identity':tid,'carrier_identity':base,'layout_identity':lid,
                'status':'candidate_title_block','block_name':scalar(head,'BlockName',True),
                'effective_block_name':scalar(entity,'EffectiveName_RAW',True),
                'attribute_count':len(attrs),'attributes':attrs,'definition_defaults':defaults,
                'basis':'PaperSpace INSERT with at least two metadata-like tag roles; lexical structure only',
                'position_size_status':'supporting_only_not_used','provenance':provenance}
            result['title_blocks'].append(tb)
            for a in attrs:
                roles=[]
                r=role(a['tag'])
                if r:roles.append((r,'layout_title_block_attribute_candidate',None))
                for g in a['field_graphs']:
                    if g['graph_complete']:
                        for n in g['nodes']:
                            for token,fr in FIELD_ROLES.items():
                                if re.search(r'(?<![A-Za-z])'+token+r'(?![A-Za-z])',n['raw_field_code']):roles.append((fr,'field_graph_backed',g))
                for r,strength,g in roles:
                    if not a['raw_value'].strip():continue
                    c={'kind':r+'_candidate','identifier_role':'unresolved' if r.startswith('unresolved') else r,
                       'value':a['raw_value'],'raw_value':a['raw_value'],'tag':a['tag'],
                       'carrier_identity':a['carrier_identity'],'source_status':a['source_status'],
                       'layout_identity':lid,'title_block_identity':tid,'evidence_strength':strength,
                       'field_graph':g,'status':'candidate','identifies_current_drawing':'candidate',
                       'provenance':provenance}
                    c['candidate_id']=digest(c);result['candidates'].append(c)
    # Conservative status, no auto-selected title block or sheet.
    for l in result['layouts']:
        if l['space_type']!='PaperSpace':continue
        cs=[c for c in result['candidates'] if c['layout_identity']==l['layout_identity']]
        numbers=[c for c in cs if c['kind'] in ('drawing_number_candidate','sheet_number_candidate','unresolved_number_candidate')]
        titles=[c for c in cs if c['kind'] in ('drawing_title_candidate','sheet_title_candidate','unresolved_title_candidate')]
        status='candidate' if numbers or titles else 'unresolved'
        kinds={c['kind'] for c in cs}
        if any(len({c['value'] for c in cs if c['kind']==k})>1 for k in kinds):status='conflicting'
        elif len({c['title_block_identity'] for c in cs})>1:status='ambiguous'
        result['sheet_candidates'].append({'project_id':instance['project_id'],'drawing_instance_id':instance['instance_id'],
          'layout_identity':l['layout_identity'],'number_candidates':numbers,'title_candidates':titles,
          'sheet_identity_status':status,'source_evidence':cs,'provenance':provenance})
    states=[s['sheet_identity_status'] for s in result['sheet_candidates']]
    state='conflicting' if 'conflicting' in states else 'ambiguous' if 'ambiguous' in states or sum(x=='candidate' for x in states)>1 else 'candidate' if 'candidate' in states else 'unresolved'
    result.update(identity_status=state,sheet_identity_status=state)
    if Path(path).read_bytes()!=data:raise ValueError('layout report changed during read')
    return result
