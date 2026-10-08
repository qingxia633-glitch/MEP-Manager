"""Explicit synthetic declarations only; not a project migration tool."""
import copy
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'post-hardening-pass3/tests'))
import test_admission as previous
ORIGINAL_PLAN = previous.complete_plan
ORIGINAL_ITEM = previous.item
PLAN_TEMPLATE = ORIGINAL_PLAN()

VERSIONS = {'authorization': 'EvidenceAuthorizationContract/1',
            'provenance': 'ProvenanceRecordContract/1',
            'assumptions': 'AssumptionDependencyPolicy/1'}


def plan():
    p = copy.deepcopy(PLAN_TEMPLATE)
    p['admission_contracts'] = dict(VERSIONS)
    gate = p['semantic_gate']; identity = copy.deepcopy(p['binding'])
    gate['accepted_evidence'][0].update(evidence_id='e', binding_id='b',
        evidence_type='human_project_confirmation', evidence_strength='direct_object_binding')
    gate['binding_targets'] = [dict(identity, binding_id='b', review_status='approved',
        evidence_ids=['e'], semantic_role=p['approved_semantic_role'], assertion='affirm',
        provenance=['synthetic authorization'])]
    sources = {}

    def citation(path):
        sid = {'/base_path':'route','/height_evidence':'synthetic-review'}.get(path,'synthetic:' + path)
        sha = hashlib.sha256(('independent synthetic source ' + path).encode()).hexdigest()
        sources[sid] = dict(source_id=sid, sha256=sha, status='verified',
            object_identity=copy.deepcopy(identity), evidence_refs=[path])
        return [dict(source_id=sid, sha256=sha, status='verified',
            object_identity=copy.deepcopy(identity), evidence_ref=path,
            binding_ref='/binding', pointer='')]

    def walk(record, path):
        if isinstance(record, dict):
            if isinstance(record.get('provenance'), list):
                record['provenance'] = citation(path)
            for key, value in record.items():
                if key != 'provenance': walk(value, path + '/' + key)
        elif isinstance(record, list):
            for i, value in enumerate(record): walk(value, path + '/' + str(i))

    for key in ('base_path','multiplier','specification','deduplication','owned_adjustments',
                'geometry_basis','height_evidence','semantic_gate','reporting_policy',
                'unit_execution_contract'):
        walk(p[key], '/' + key)
    # Raw audit is the identical evidence record, not a second approval.
    p['unit_execution_contract']['raw_geometry_conversion'] = copy.deepcopy(p['geometry_basis']['conversion'])
    sources.pop('synthetic:/unit_execution_contract/raw_geometry_conversion', None)
    p['source_evidence_hashes'] = sources
    p['provenance'] = copy.deepcopy(sources)
    previous.seal(p['reporting_policy'])
    return previous.seal(p)


def item():
    x=ORIGINAL_ITEM();p=plan()
    for sid in list(p['source_evidence_hashes']):
        if '/unit_execution_contract/' in sid:p['source_evidence_hashes'].pop(sid)
    x['verified_sources']=copy.deepcopy(p['source_evidence_hashes'])
    for target,origin in [('semantic_gate','semantic_gate'),('geometry','geometry_basis'),('height','height_evidence'),
                          ('base_path','base_path'),('specification','specification'),('multiplier','multiplier'),
                          ('deduplication','deduplication'),('assumptions','assumptions')]:
        x[target]=copy.deepcopy(p[origin])
    x['height_requirement']='required';x['admission_contracts']=dict(VERSIONS)
    x['adjustments']['transition']['items']=copy.deepcopy(p['owned_adjustments'])
    return x


def parameter_plan(multiplier=1,unit='m'):
    p=plan();p['multiplier']['value']=multiplier
    p['unit_execution_contract']['multiplier'].update(original_value=str(multiplier),normalized_value=str(multiplier))
    if unit=='mm':
        g=p['geometry_basis'];g.update(base_length='10000',source_unit='mm',engineering_unit='mm')
        g['conversion'].update(from_unit='mm',to_unit='mm',converted_length='10000')
        p['unit_conversion_contract'].update(source_unit='mm',target_unit='mm')
        p['unit_execution_contract']['raw_geometry_conversion']=copy.deepcopy(g['conversion'])
        for i,r in enumerate([p['base_path']]+p['owned_adjustments']):
            v=['10000','200','300'][i];r['unit']='mm';r['value' if i==0 else 'length']=v
            t=p['unit_execution_contract']['components'][i];t.update(original_value=v,original_unit='mm');t['conversion'].update(source_unit='mm',factor='0.001')
    return previous.seal(p)


def assumption(p, refs=None):
    sid='synthetic:assumption'; h=hashlib.sha256(sid.encode()).hexdigest()
    src=dict(source_id=sid,sha256=h,status='verified',object_identity=copy.deepcopy(p['binding']),evidence_refs=['/assumptions/0'])
    p['source_evidence_hashes'][sid]=src;p['provenance'][sid]=copy.deepcopy(src)
    a=dict(id='A',status='approved',value='synthetic leaf',scope=dict(binding=copy.deepcopy(p['binding']),conditions={'slab':300}),
        provenance=[dict(source_id=sid,sha256=h,status='verified',object_identity=copy.deepcopy(p['binding']),
                         evidence_ref='/assumptions/0',binding_ref='/binding',pointer='')])
    if refs is not None:a.update(assumptions_required=True,assumption_refs=refs)
    p['assumptions']=[a]
    p['height_evidence'].update(assumptions_required=True,assumption_refs=['A'],conditions={'slab':300})
    return p


def cite_synthetic(p, record, path):
    sid='synthetic:'+path;h=hashlib.sha256(sid.encode()).hexdigest()
    p['source_evidence_hashes'][sid]=dict(source_id=sid,sha256=h,status='verified',object_identity=copy.deepcopy(p['binding']),evidence_refs=[path])
    p['provenance']=copy.deepcopy(p['source_evidence_hashes'])
    record['provenance']=[dict(source_id=sid,sha256=h,status='verified',object_identity=copy.deepcopy(p['binding']),evidence_ref=path,binding_ref='/binding',pointer='')]


def planar():
    p=plan();p['owned_adjustments']=[]
    p['formula_components']['arguments'][0]['references']=['base_path.value']
    p['unit_execution_contract']['components']=p['unit_execution_contract']['components'][:1]
    p['height_requirement']='not_applicable'
    p['height_evidence'].update(status='not_applicable',reason='Independent synthetic approved planar measurement')
    p['height_evidence']['measurement_rule']=dict(rule_id='synthetic-planar/1',status='approved',binding=copy.deepcopy(p['binding']),measurement_mode='converted_2d',height_requirement='not_applicable')
    for sid in list(p['source_evidence_hashes']):
        if '/owned_adjustments/' in sid or any('/unit_execution_contract/components/'+str(i) in sid for i in (1,2)):
            p['source_evidence_hashes'].pop(sid)
    cite_synthetic(p,p['height_evidence']['measurement_rule'],'/height_evidence/measurement_rule')
    return previous.seal(p)
