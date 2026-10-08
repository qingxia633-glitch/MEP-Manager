"""Additive provenance verification for saved, already approved project records.

No engineering approval is added: status=verified describes hash/pointer checking.
Fallbacks name the precise historical approval record rather than inventing a source.
Original field values and hashes remain in the per-field migration log.
"""
import copy
import hashlib
import json
from pathlib import Path
from synthetic_contract import VERSIONS, previous

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/post-hardening-pass4-20261009'


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pointer(value,path):
    for key in path.split('/')[1:] if path else []:
        key=key.replace('~1','/').replace('~0','~')
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value


def migrate(kind):
    source=ROOT/('outputs/post-hardening-pass3-20261008/golden-'+kind+'-v03.json')
    document=read(source);old=document['fixture'];p=copy.deepcopy(old)
    identity=copy.deepcopy(p['binding']);sources={};changes=[]
    def change(record,key,value,path,refs,reason):
        if record.get(key)==value:return
        changes.append(dict(path=path,old_value=copy.deepcopy(record.get(key)),new_value=copy.deepcopy(value),
                            source_evidence=refs,derivation=reason))
        record[key]=copy.deepcopy(value)
    def ref(path,location):
        pointer(read(path),location)
        return dict(path=str(path.relative_to(ROOT)).replace('\\','/'),sha256=sha(path),pointer=location)
    def cite(record,path):
        raw=record.get('provenance')
        if not isinstance(raw,list) or not raw:raise ValueError('No real source at '+path)
        links=[]
        for item in raw:
            if isinstance(item,dict) and item.get('source_id') in old['source_evidence_hashes'] and 'pointer' in item:
                s=old['source_evidence_hashes'][item['source_id']];f=Path(s['path'])
                if sha(f)!=s['sha256']:raise ValueError('Historical source hash changed')
                links.append(ref(f,item['pointer']))
            else:
                # This is an archived approval declaration, not a reconstructed drawing fact.
                links.append(ref(source,'/fixture'+path+'/provenance'))
        new=[]
        for link in links:
            sid=link['path'];entry=sources.setdefault(sid,dict(source_id=sid,sha256=link['sha256'],
                status='verified',object_identity=copy.deepcopy(identity),evidence_refs=[],path=sid))
            if path not in entry['evidence_refs']:entry['evidence_refs'].append(path)
            new.append(dict(source_id=sid,sha256=link['sha256'],status='verified',object_identity=copy.deepcopy(identity),
                evidence_ref=path,binding_ref='/binding',pointer=link['pointer']))
        change(record,'provenance',new,path+'/provenance',links,'Verify existing source hash/pointer; retain prior approval without inventing it')
    def walk(x,path):
        if isinstance(x,dict):
            if isinstance(x.get('provenance'),list):cite(x,path)
            for key,value in x.items():
                if key!='provenance':walk(value,path+'/'+key)
        elif isinstance(x,list):
            for i,value in enumerate(x):walk(value,path+'/'+str(i))
    gate=p['semantic_gate']
    for i,binding in enumerate(gate['binding_targets']):
        applicable=[e for e in gate['accepted_evidence'] if e['binding_id']==binding['binding_id']]
        if not applicable or {e['semantic_role'] for e in applicable}!={p['approved_semantic_role']}:
            raise ValueError('No unique reviewed binding role')
        for key in ('semantic_role','assertion'):
            refs=[ref(source,'/fixture/semantic_gate/accepted_evidence/'+str(gate['accepted_evidence'].index(e))+'/'+key) for e in applicable]
            change(binding,key,applicable[0][key],'/semantic_gate/binding_targets/'+str(i)+'/'+key,refs,'Materialize role/assertion of the existing exact reviewed evidence binding')
    for key in ('base_path','multiplier','specification','deduplication','owned_adjustments','geometry_basis',
                'height_evidence','assumptions','reporting_policy','corrections_applied','unit_execution_contract'):
        if key=='unit_execution_contract':
            for i,term in enumerate(p[key]['components']):cite(term,'/'+key+'/components/'+str(i))
            cite(p[key]['multiplier'],'/'+key+'/multiplier')
        else:walk(p[key],'/'+key)
    for group in ('accepted_evidence','binding_targets'):
        for i,record in enumerate(gate[group]):cite(record,'/semantic_gate/'+group+'/'+str(i))
    p['unit_execution_contract']['raw_geometry_conversion']=copy.deepcopy(p['geometry_basis']['conversion'])
    p['source_evidence_hashes']=sources;p['provenance']=copy.deepcopy(sources)
    p['admission_contracts']=dict(VERSIONS)
    previous.seal(p['reporting_policy'])
    if p['corrections_applied'].get('evidence'):previous.seal(p['corrections_applied']['evidence'])
    previous.seal(p)
    return dict(migration_id='pass4-'+kind,source_fixture=ref(source,''),
                policy='verified source records, no new engineering approval',historical_files_modified=False,
                changes=changes,fixture=p)


if __name__=='__main__':
    for kind in ('conduit','wire'):
        value=migrate(kind)
        with (OUT/('golden-'+kind+'-profile1.json')).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
