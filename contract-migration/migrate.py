"""Project-only, additive source-backed input migration. Never rewrites source artifacts."""
import copy
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/source-backed-contract-migration-20261008'
VERSION = 'source-backed-input-migration/1'
SNAPSHOT = 'local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'
PLAN_DIR = 'outputs/quantity-build-plan-v02'
BUNDLE = 'project-evidence-gate/project-evidence/garage-golden.json'
ITEMS = 'quantity-eligibility/fixtures/golden.json'
ROUTE = 'outputs/golden-3d-route-20261004/evidence.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def load(folder, filename='resolver.py'):
    for name in ('resolver','evidence','model','rules','annotations','bindings'):
        sys.modules.pop(name,None)
    sys.path.insert(0,str(ROOT/folder))
    spec=importlib.util.spec_from_file_location('migration_'+folder.replace('-','_')+filename.replace('.','_'),ROOT/folder/filename)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def source(path, pointer='', **extra):
    return dict(path=path,sha256=sha(ROOT/path),pointer=pointer,**extra)


def pointer(value, path):
    for token in path.strip('/').split('/') if path else []:
        token=token.replace('~1','/').replace('~0','~')
        value=value[int(token)] if isinstance(value,list) else value[token]
    return value


def top_level_identity(snapshot, edge, project, scope):
    text=(ROOT/snapshot).read_text(encoding='utf-8-sig')
    header=text.split('EntityHandle=',1)[0]
    if ('AcquisitionMode="ModelSpaceTopLevelAllLayers"' not in header or
        'ModelSpaceTopLevel="included"' not in header or 'NestedBlocks="not expanded"' not in header):
        raise ValueError('No explicit ModelSpace-only extraction evidence')
    records=[r for r in re.split(r'(?m)(?=^EntityHandle=)',text)
             if re.match(r'EntityHandle="'+re.escape(edge)+r'"(?:\r?\n|$)',r)]
    if len(records)!=1:
        raise ValueError('Unique top-level edge record required')
    record=records[0]
    if 'DXF_Type="LWPOLYLINE"' not in record and 'DXF_Type="LINE"' not in record:
        raise ValueError('Expected real route geometry')
    drawing=re.search(r'^DWG="(.*)"',header,re.M)[1].replace('\\','/').split('/')[-1]
    if scope!='edge':
        raise ValueError('This project migration has no source for segment boundaries')
    line=text[:text.index('EntityHandle="'+edge+'"')].count('\n')+1
    return dict(project_id=project,drawing_ref=drawing,parent_path=[],edge_handle=edge,scope_type=scope),source(snapshot,handle=edge,line=line,extraction_scope='ModelSpaceTopLevelAllLayers')


def complete_bound_identities(value, identity):
    """Only exact reviewed project/edge bindings; no default for unrelated instances."""
    if isinstance(value,dict):
        if all(k in value for k in ('project_id','drawing_ref','edge_handle')):
            if value['project_id']!=identity['project_id'] or value['edge_handle']!=identity['edge_handle']:
                raise ValueError('Foreign bound identity cannot be migrated by this source')
            if value.get('segment_id') is not None:
                raise ValueError('No independent segment boundary source')
            if 'parent_path' in value and value['parent_path']!=identity['parent_path']:
                raise ValueError('Existing instance path conflicts with source')
            value.update(copy.deepcopy(identity))
        for k,v in value.items():
            # Preserve embedded signed correction evidence exactly.
            if k!='corrections_applied':complete_bound_identities(v,identity)
    elif isinstance(value,list):
        for v in value:complete_bound_identities(v,identity)


def changes(old,new,path=''):
    rows=[]
    if isinstance(old,dict) and isinstance(new,dict):
        for k,v in new.items():
            p=path+'/'+k.replace('~','~0').replace('/','~1')
            if k not in old:rows.append(dict(path=p,operation='add',value=copy.deepcopy(v)))
            else:rows.extend(changes(old[k],v,p))
        for k in old.keys()-new.keys():rows.append(dict(path=path+'/'+k,operation='remove',historical_value=old[k]))
    elif old!=new:
        rows.append(dict(path=path,operation='replace',historical_value=copy.deepcopy(old),value=copy.deepcopy(new)))
    return rows


def package(name,old,new,source_fixture,old_version,sources,status='contract_complete',missing=None):
    rows=changes(old,new)
    # Every changed field is linked to the exact input plus the verified source set.
    # Mechanical fields (hash/record) are DerivedInference, never DrawingFact.
    for row in rows:
        row['source_evidence']=copy.deepcopy(sources)
        row['evidence_type']='DerivedInference'
        if row['path'].endswith('/parent_path'):
            row['source_evidence']=[s for s in sources if s.get('extraction_scope')]
            row['evidence_type']='DrawingFact'
        elif row['path'].endswith('/scope_type'):
            row['source_evidence']=[s for s in sources if s.get('pointer')=='/objects/0/measurement_scope/kind']
        elif row['path'].endswith('/drawing_ref'):
            row['source_evidence']=[s for s in sources if s.get('extraction_scope')]
        if not row['source_evidence']:raise ValueError('Unsourced migration field '+row['path'])
    return dict(migration_id=name,source_fixture=source_fixture,
        target_fixture='outputs/source-backed-contract-migration-20261008/fixtures/'+name+'.json',
        old_schema_version=old_version,new_schema_version='input-contract/2 (QuantityBuildPlan schema remains 0.2)',
        added_fields=[r['path'] for r in rows if r['operation']=='add'],
        source_evidence_for_each_added_field={r['path']:r['source_evidence'] for r in rows if r['operation']=='add'},
        field_changes=rows,migration_reason='Explicit instance identity and required evidence contract; no historical rewrite',
        migrated_at=datetime.now(timezone.utc).isoformat(),migration_tool=dict(name=VERSION,sha256=sha(__file__)),
        status=status,missing_evidence=missing or [],historical_files_modified=False,fixture=new)


def save(wrapper):
    p=ROOT/wrapper['target_fixture'];p.parent.mkdir(parents=True,exist_ok=True)
    wrapper['fixture_hash']=digest(wrapper['fixture'])
    wrapper['record_hash']=digest(wrapper)
    with p.open('x',encoding='utf-8') as f:json.dump(wrapper,f,ensure_ascii=False,indent=2)
    return wrapper


def create():
    OUT.mkdir(exist_ok=True)
    evidence=load('quantity-eligibility','evidence.py').load_evidence(ROOT/ITEMS)
    gb=load('project-evidence-gate','evidence.py').load_bundle(ROOT/BUNDLE)
    edge=evidence['objects'][0]['measurement_scope']['binding']['edge_handle']
    scope=evidence['objects'][0]['measurement_scope']['kind']
    identity,snap=top_level_identity(SNAPSHOT,edge,gb['project_id'],scope)
    correction=read(PLAN_DIR+'/correction-evidence.json')
    if correction['corrected_value']!=identity['drawing_ref'] or correction['provenance'][0]['sha256']!=snap['sha256']:
        raise ValueError('Existing correction/source snapshot mismatch')
    route=read(ROUTE)
    if route['status']!='supported' or any(s['status']!='supported' for s in route['slabFollowingSegments']+route['endpointTransitions']):
        raise ValueError('Missing supported source height/geometry')
    for path,h in route['sourceHashes'].items():
        if sha(ROOT/path)!=h:raise ValueError('Route source hash mismatch')
    sources=[snap,source(BUNDLE,'/project_id'),source(ITEMS,'/objects/0/measurement_scope/kind'),
             source(ROUTE,'/slabFollowingSegments'),source(ROUTE,'/endpointTransitions'),
             source(PLAN_DIR+'/correction-evidence.json'),source('quantity-eligibility/unit_contract.py',evidence_type='SoftwareContract')]
    raw_candidate=copy.deepcopy(evidence['objects'][0]['semantic_gate']['provenance']['candidate'])
    original=dict(candidate=raw_candidate,bundle=copy.deepcopy(gb),context=copy.deepcopy(evidence['objects'][0]['semantic_gate']['provenance']['context']))
    candidate=copy.deepcopy(raw_candidate);candidate.update(identity)
    bundle=copy.deepcopy(gb);bundle['drawing_ref']=identity['drawing_ref'];complete_bound_identities(bundle,identity)
    context=copy.deepcopy(identity)
    gate_inputs=dict(candidate=candidate,bundle=bundle,context=context)
    gate=load('project-evidence-gate').evaluate_semantics(**gate_inputs)
    if not gate['semantic_gate_passed']:raise ValueError('Source-backed Gate failed')
    saved=[save(package('golden-gate-v2',original,gate_inputs,source(BUNDLE),'legacy Gate input',sources))]
    for index,kind in enumerate(('conduit','wire')):
        source_plan=PLAN_DIR+'/golden-'+kind+'-v02.json'
        old=read(source_plan);p=copy.deepcopy(old)
        # Assert the preserved approved 3D value against the underlying source, not a test literal.
        if p['base_path']['value']!=route['slabFollowingLengthMeters']:raise ValueError('Source path mismatch')
        for record in (p['geometry_basis'],p['height_evidence']):
            if record['status']!='supported' or not record['provenance']:raise ValueError('Legacy evidence missing')
            for ref in record['provenance']:
                src=p['source_evidence_hashes'][ref['source_id']]
                path=Path(src['path'])
                if not path.exists() or sha(path)!=src['sha256']:raise ValueError('Plan source hash mismatch')
                pointer(json.loads(path.read_text(encoding='utf-8-sig')),ref.get('pointer',''))
        complete_bound_identities(p,identity)
        p['height_requirement']='required'
        p['unit_conversion_contract']=load('quantity-eligibility','unit_contract.py').conversion_contract(p['geometry_basis']['conversion'],p['binding'])
        # Existing frozen correction record and arithmetic components are retained byte-for-byte as JSON values.
        p['content_hash']=digest({k:v for k,v in p.items() if k!='content_hash'})
        saved.append(save(package('golden-'+kind+'-plan-v2',old,p,source(source_plan),'QuantityBuildPlan/0.2 legacy identity',sources+[source(source_plan)])))
        old_item=evidence['objects'][index];x=copy.deepcopy(old_item)
        complete_bound_identities(x,identity)
        x['semantic_gate']=copy.deepcopy(gate)
        x['height_requirement']='required'
        x['unit_conversion_contract']=copy.deepcopy(p['unit_conversion_contract'])
        saved.append(save(package('golden-'+kind+'-eligibility-v2',old_item,x,source(ITEMS,'/objects/'+str(index)),'QuantityEligibility/0.1 legacy identity',sources+[source(ITEMS,'/objects/'+str(index))])))
    # No migration of synthetic identity, geometry or height into real project evidence.
    f=load('safety-hardening','fixtures.py')
    for name,value in [('synthetic-item',f.item()),('synthetic-plan',f.plan())]:
        saved.append(save(package(name+'-legacy-incomplete',value,copy.deepcopy(value),source('safety-hardening/fixtures.py',name),'synthetic legacy/1',
            [source('safety-hardening/fixtures.py',name)],status='legacy_incomplete',
            missing=['No real instance parent_path source','No real height evidence for endpoint transitions; not_applicable is not approval'])))
    # Gate and applicability synthetic identities have no drawing source either.
    saved.append(save(package('synthetic-gate-legacy-incomplete',{}, {}, source('project-evidence-gate/tests/test_resolver.py','candidate/bundle/run'),'synthetic legacy/1',
        [source('project-evidence-gate/tests/test_resolver.py')],status='legacy_incomplete',missing=['No real identity or parent_path source; original callable fixtures retained'])))
    with (OUT/'migration-manifest.json').open('x',encoding='utf-8') as f:
        json.dump([dict(migration_id=s['migration_id'],target_fixture=s['target_fixture'],status=s['status'],record_hash=s['record_hash']) for s in saved],f,ensure_ascii=False,indent=2)
    print([(s['migration_id'],s['status']) for s in saved])

if __name__=='__main__':create()
