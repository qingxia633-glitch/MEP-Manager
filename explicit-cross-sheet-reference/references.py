"""Explicit source observations and candidate lookup, never semantic approval."""
from copy import deepcopy
from pathlib import Path, PureWindowsPath
import re
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'project-drawing-registry'))
sys.path.insert(0, str(ROOT/'project-evidence-discovery'))
from registry import content_hash, lookup
from field_graph import graph_record
from leader_contract import validate_leader_evidence_record

ALIAS_KINDS = {'source_filename','filename_stem','drawing_number_candidate',
               'drawing_title_candidate','sheet_number_candidate'}
CUE = re.compile(r'详见|参见|详图见|做法见|(?<![\w\u4e00-\u9fff])见|按(?=[^。；;\n]{1,100}图)')
NUMBER = re.compile(r'[A-Za-z]{1,8}-[0-9]+(?:[.-][0-9]+)*(?![A-Za-z0-9_./\\-])')
FIELD_PROPERTY = re.compile(r'(?<![\w])(?:SheetNumber|SheetTitle|SheetView|ViewNumber|ViewTitle)(?![\w])')

def extract_text(text):
    """Do not remove punctuation/spacing or consult the registry to invent IDs."""
    results=[]
    for occurrence, cue in enumerate(CUE.finditer(text)):
        stop=re.search(r'[。；;\r\n]',text[cue.end():])
        end=cue.end()+stop.start() if stop else len(text)
        phrase=text[cue.end():end].strip()
        identifiers=[]; rest=phrase
        # Only leading identifiers and explicitly separated lists, not every code
        # elsewhere in a sentence. Surrounding quotation is retained in raw text.
        if rest.startswith(('《','「','"')):rest=rest[1:]
        while rest:
            m=NUMBER.match(rest)
            if not m:break
            identifiers.append((m[0],'drawing_number_reference'))
            tail=rest[m.end():]
            sep=re.match(r'\s*[、,，]\s*',tail)
            if not sep:break
            rest=tail[sep.end():]
        if not identifiers:
            # Do not trim an unparseable numerical token to a shorter title.
            title=phrase
            if title.startswith('《') and title.endswith('》'):title=title[1:-1]
            if re.fullmatch(r'[\u4e00-\u9fffA-Za-z0-9（）() _.-]{1,150}\.dwg',title,re.I):
                identifiers=[(title,'cross_sheet_text_reference')]
            elif re.fullmatch(r'[\u4e00-\u9fffA-Za-z0-9（）() _-]{1,100}(?:图|大样)',title):
                identifiers=[(title,'drawing_title_reference')]
        if not identifiers:identifiers=[(None,'unknown_explicit_reference')]
        for index,(identifier,typ) in enumerate(identifiers):
            results.append({'reference_type':typ,'raw_reference_text':text[cue.start():end],
                'reference_span':[cue.start(),end],'occurrence_index':occurrence,'identifier_index':index,
                'identifier_raw':identifier,'identifier_normalized':identifier,
                'normalization_status':'unchanged' if identifier else 'unresolved',
                'target_identifier_status':'candidate' if identifier else 'unresolved'})
    return results

def validate_registry(registry):
    if type(registry.get('registry_version')) is not int or registry['registry_version']!=1 or not isinstance(registry.get('project_id'),str) or not registry['project_id'].strip():
        raise ValueError('Registry v1 with explicit project required')
    instances={}
    for d in registry.get('drawing_instances',[]):
        basis={k:d.get(k) for k in ('project_id','drawing_ref','source_dwg_sha256','report_sha256')}
        if (basis['project_id']!=registry['project_id'] or not isinstance(basis['drawing_ref'],str)
            or not basis['drawing_ref'] or not re.fullmatch('[0-9a-f]{64}',basis['report_sha256'] or '')
            or content_hash(basis)!=d.get('instance_id') or d['instance_id'] in instances):
            raise ValueError('Invalid or duplicate registry instance identity')
        instances[d['instance_id']]=d
    if not instances:raise ValueError('No registered instances')
    for a in registry.get('aliases',[]):
        d=instances.get(a.get('instance_id'))
        if (not d or a.get('kind') not in ALIAS_KINDS or not isinstance(a.get('value'),str)
            or not a['value'].strip() or a.get('status') not in ('observed','candidate','partial')
            or not any(p.get('source_type')=='report_bytes' and p.get('sha256')==d['report_sha256'] for p in a.get('provenance',[]) if isinstance(p,dict))):
            raise ValueError('Unbound or unsupported registry alias evidence')
        src=a.get('source_identity',{})
        if src.get('project_id',registry['project_id'])!=registry['project_id'] or src.get('snapshot_id',d['report_sha256'])!=d['report_sha256']:
            raise ValueError('Foreign alias identity')
    return instances

def _valid(identity, context, provenance):
    return (identity.get('project_id')==context['project_id']
        and identity.get('drawing_ref')==context['drawing_ref']
        and identity.get('snapshot_id')==context['snapshot_id']
        and isinstance(identity.get('parent_path'),list)
        and all(isinstance(x,str) and x for x in identity['parent_path'])
        and isinstance(identity.get('handle') or identity.get('table_handle'),str)
        and bool(identity.get('handle') or identity.get('table_handle'))
        and bool(provenance) and all(isinstance(p,dict) and p.get('sha256')==context['snapshot_id'] for p in provenance))

def _observations(c):
    observations=[];excluded=[]
    def add(identity,sub,text,raw,status,typ,provenance,relations=None,owner=None):
        if not _valid(identity,c,provenance) or not isinstance(text,str):
            excluded.append({'identity':identity,'reason':'missing_or_foreign_identity_text_or_provenance'});return
        observations.append({'carrier_identity':deepcopy(identity),'subelement_identity':deepcopy(sub),
          'text':text,'raw_serialized_text':raw,'status':status,'carrier_type':typ,
          'provenance':deepcopy(provenance),'source_relations':deepcopy(relations or []),'owner_insert_identity':deepcopy(owner)})
    for a in c.get('annotations',[]):
        typ=a.get('type');path=a.get('parent_path')
        if typ not in ('TEXT','MTEXT','ATTRIB','MLEADER_MTEXT','MLEADER_CONTENT_UNRESOLVED'):continue
        i={'project_id':a.get('project_id'),'drawing_ref':a.get('source_drawing'),
           'snapshot_id':c['snapshot_id'],'handle':a.get('handle'),'parent_path':path}
        relations=[];owner=a.get('owner_insert_identity');status='supported'
        if typ.startswith('MLEADER'):
            leaders=[l for l in c.get('leaders',[]) if l.get('handle')==a.get('handle') and l.get('parent_path')==path]
            if len(leaders)==1:
                i.update(project_id=leaders[0].get('project_id'),drawing_ref=leaders[0].get('source_drawing'))
            status='partial'
        if typ=='ATTRIB':
            if (not isinstance(owner,dict) or not path or owner.get('handle')!=path[-1]
                or owner.get('parent_path')!=path[:-1] or owner.get('project_id')!=i['project_id']
                or owner.get('drawing_ref')!=i['drawing_ref']):
                excluded.append({'identity':i,'reason':'attribute_owner_incomplete_or_foreign'});continue
        if a.get('text_decode_status')!='read':
            excluded.append({'identity':i,'reason':'text_decode_not_read'});continue
        # Exact carrier matching, not spatial matching. Dynamic/mixed content is
        # only an observed display and cannot be promoted to authored static text.
        if any(all(f.get('carrier_identity',{}).get(k)==i[k] for k in i) for f in c.get('field_evidence',[])):
            status='partial'
        for l in c.get('leaders',[]):
            if l.get('type')=='LEADER' and l.get('annotation_handle')==a.get('handle'):
                checked=validate_leader_evidence_record(l,c['annotations'],c)
                if checked['association_status']=='explicit':
                    relations.append({'type':'classic_leader_source_relation','leader_handle':l['handle'],
                        'parent_path':l['parent_path'],'validation':checked,'provenance':l['provenance']})
        if typ=='MTEXT':
            structure=a.get('mtext_structure',{})
            for p in structure.get('paragraphs',[]):
                expected=dict(i,paragraph_index=p.get('paragraph_index'),source_span=p.get('source_span'))
                if p.get('identity')!=expected:
                    excluded.append({'identity':i,'reason':'foreign_paragraph_identity'});continue
                add(i,p['identity'],p.get('decoded_text'),p.get('raw_fragment'),
                    status if p.get('structure_status')=='read' else 'partial',typ,p.get('provenance'),relations,owner)
            if not structure.get('paragraphs'):excluded.append({'identity':i,'reason':'paragraph_structure_missing'})
        else:add(i,None,a.get('decoded_text'),a.get('raw_serialized_text'),status,typ,a.get('provenance'),relations,owner)
    for table in c.get('table_evidence',[]):
        for cell in table.get('cells',[]):
            i=cell.get('identity',{});kind=cell.get('content_kind')
            if cell.get('text_decode_status')!='read' or kind not in ('text_observation','field'):
                excluded.append({'identity':i,'reason':'cell_not_readable_text_or_field_display'});continue
            if any(type(i.get(k))!=int or i[k]<0 for k in ('row_index','column_index')):
                excluded.append({'identity':i,'reason':'cell_identity_missing'});continue
            add(i,dict(i,subelement_type='table_cell'),cell.get('decoded_text'),cell.get('raw_content'),
                'partial' if kind=='field' else 'supported','TABLE_CELL',table.get('provenance'))
    field_coverage={'fields_inspected':len(c.get('field_evidence',[])),'sheet_view_property_candidates':0,'field_nodes_inspected':0,'complete_graphs':0}
    for f in c.get('field_evidence',[]):
        i=f.get('carrier_identity',{});prov=f.get('provenance',[])
        if not _valid(i,c,prov):
            excluded.append({'identity':i,'reason':'field_identity_or_provenance_invalid'});continue
        g=graph_record(f.get('raw_field_record',''),i,prov)
        field_coverage['field_nodes_inspected']+=len(g['nodes'])
        field_coverage['complete_graphs']+=int(g['graph_complete'])
        for node in g['nodes']:
            code=node.get('raw_field_code') or ''
            if node.get('unresolved_reasons'):
                excluded.append({'identity':node['identity'],'reason':'invalid_field_node','details':node['unresolved_reasons']});continue
            if node.get('field_code_status')!='read' or not FIELD_PROPERTY.search(code):continue
            field_coverage['sheet_view_property_candidates']+=1
            # Property tokens are observed in actual FIELD records. The evaluator
            # and remote sheet identity grammar is not approved by this contract.
            add(i,node['identity'],code,code,'partial','FIELD',prov,
                [{'type':'field_graph_property_candidate','graph_complete':g['graph_complete'],
                  'field_node':node,'object_references':g['object_references']}])
    return observations,excluded,field_coverage

def scan(registry,contexts):
    instances=validate_registry(registry);project=registry['project_id']
    observations=[];excluded=[];coverage=[];input_sources=[];carrier_coverage=[]
    for c in contexts:
        if c.get('project_id')!=project or c.get('report_integrity')!='verified':
            raise ValueError('Foreign project or unverified context')
        matches=[d for d in instances.values() if d['report_sha256']==c.get('snapshot_id')
                 and d.get('report_identity')==c.get('report_identity')]
        if len(matches)!=1 or PureWindowsPath(matches[0]['drawing_ref']).name!=c.get('drawing_ref'):
            raise ValueError('Source acquisition not uniquely registered')
        d=matches[0];obs,ex,cov=_observations(c)
        for o in obs:o['source_drawing_instance_id']=d['instance_id']
        observations.extend(obs);excluded.extend(ex);coverage.append(dict(cov,source_drawing_instance_id=d['instance_id']))
        carrier_coverage.append({'source_drawing_instance_id':d['instance_id'],
            'annotations_inspected':dict(sorted(Counter(a.get('type','unknown') for a in c.get('annotations',[])).items())),
            'mtext_paragraphs_inspected':sum(len(a.get('mtext_structure',{}).get('paragraphs',[])) for a in c.get('annotations',[])),
            'table_cells_inspected':sum(len(t.get('cells',[])) for t in c.get('table_evidence',[])),
            'leaders_inspected':dict(sorted(Counter(l.get('type','unknown') for l in c.get('leaders',[])).items()))})
        input_sources.append({'source_drawing_instance_id':d['instance_id'],'report_sha256':c['snapshot_id']})
    # Contradictory contents detected BEFORE cue filtering, including versions
    # where the same carrier no longer contains any explicit reference.
    groups={}
    for o in observations:
        # A paragraph's span is derived from its content, not an escape hatch for
        # contradictory versions of the same paragraph index in one snapshot.
        anchor=deepcopy(o['subelement_identity'])
        if isinstance(anchor,dict):anchor.pop('source_span',None)
        sk=content_hash([project,o['source_drawing_instance_id'],o['carrier_identity'],anchor])
        groups.setdefault(sk,[]).append(o)
    conflicts=[];refs={}
    for sk,items in sorted(groups.items()):
        conflicting=len({content_hash([o['text'],o['raw_serialized_text']]) for o in items})>1
        if conflicting:conflicts.append({'source_identity_key':sk,'reason':'contradictory_source_content','observations':items})
        for o in items:
            if o['carrier_type']=='FIELD':
                tokens=FIELD_PROPERTY.findall(o['text'])
                extracted=[{'reference_type':'field_view_reference' if any('View' in t for t in tokens) else 'field_sheet_reference',
                    'raw_reference_text':o['text'],'reference_span':[0,len(o['text'])],'occurrence_index':0,'identifier_index':0,
                    'identifier_raw':None,'identifier_normalized':None,'normalization_status':'unresolved','target_identifier_status':'unresolved'}]
            else:extracted=extract_text(o['text'])
            for x in extracted:
                rid=content_hash([project,o['source_drawing_instance_id'],o['carrier_identity'],o['subelement_identity'],x])
                q=x['identifier_normalized'];match=lookup(registry,q) if q else {'lookup_status':'not_attempted','matches':[],'match_evidence':[],'logical_identity_approved':False}
                targets=match['matches'];resolution='unresolved_target'
                if len(targets)>1:resolution='ambiguous'
                elif len(targets)==1:resolution='local_reference_candidate' if targets[0]==o['source_drawing_instance_id'] else 'unique_candidate_match'
                if o['status']!='supported':resolution='unresolved_source' if resolution not in ('ambiguous','unresolved_target') else resolution
                if conflicting:resolution='conflicting_source'
                item=dict(x,reference_id=rid,project_id=project,source_drawing_instance_id=o['source_drawing_instance_id'],
                    source_carrier_identity=o['carrier_identity'],source_subelement_identity=o['subelement_identity'],
                    carrier_type=o['carrier_type'],source_text=o['text'],raw_serialized_text=o['raw_serialized_text'],
                    owner_insert_identity=o['owner_insert_identity'],source_relations=o['source_relations'],
                    reference_extraction_status='conflicting' if conflicting else o['status'],
                    target_lookup_query=q,target_lookup_status=match['lookup_status'],target_candidate_instance_ids=targets,
                    lookup_normalization_contract='Registry v1 exact NFC/casefold/outer whitespace; separators retained',
                    target_alias_evidence=match['match_evidence'],resolution_status=resolution,
                    cross_sheet_resolution_status=resolution,supported_identity_match=False,provenance=o['provenance'])
                if rid in refs:
                    old=refs[rid];old['provenance']=_unique(old['provenance']+item['provenance'])
                    old['source_relations']=_unique(old['source_relations']+item['source_relations'])
                    if item['reference_extraction_status']!='supported':
                        old.update(reference_extraction_status=item['reference_extraction_status'],resolution_status=resolution,cross_sheet_resolution_status=resolution)
                else:refs[rid]=item
    rows=[refs[k] for k in sorted(refs)]
    candidates=[r for r in rows if r['resolution_status']=='unique_candidate_match']
    ambiguous=[r for r in rows if r['resolution_status']=='ambiguous']
    unresolved=[r for r in rows if r['resolution_status'] not in ('unique_candidate_match','ambiguous','conflicting_source')]
    return {'version':1,'project_id':project,'source_references':rows,'resolved_links':[],
        'candidate_links':candidates,'ambiguous_links':ambiguous,'unresolved_references':unresolved,'conflicts':conflicts,
        'excluded_evidence':_unique(excluded),'field_coverage':_unique(coverage),
        'carrier_coverage':_unique(carrier_coverage),
        'field_sheet_reference_coverage':'absent' if not any(c['sheet_view_property_candidates'] for c in coverage) else 'partial_property_candidates',
        'summary':{'source_reference_count':len(rows),'references_with_identifier':sum(r['identifier_raw'] is not None for r in rows),
            'unique_registry_candidates':sum(len(r['target_candidate_instance_ids'])==1 for r in rows),
            'supported_resolutions':0,'partial_resolutions':len(candidates),'ambiguous':len(ambiguous),
            'unresolved':len(unresolved),'conflicts':len(conflicts)},
        'provenance':_unique(input_sources),'scope_limitation':'Native explicit-reference candidates only; no engineering or logical identity approval'}

def _unique(items):return [v for _,v in sorted({content_hash(x):x for x in items}.items())]
