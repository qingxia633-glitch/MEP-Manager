"""Reviewed project evidence vocabulary and hash-checked JSON source bindings."""
import hashlib
import json
from pathlib import Path

DIRECT_STRENGTHS = {'direct_object_binding','direct_local_design_binding','system_mapping','project_rule_binding'}
WEAK_STRENGTHS = {'pattern_only','contextual_only','external_generic'}
DIRECT_TYPES = {
    'edge_annotation': {'direct_object_binding'},
    'circuit_bus_identifier': {'direct_object_binding','system_mapping'},
    'local_wiring_diagram': {'direct_local_design_binding'},
    'system_diagram_mapping': {'system_mapping'},
    'unique_design_statement': {'project_rule_binding'},
    'reviewed_project_rule': {'project_rule_binding'},
    'human_project_confirmation': {'direct_object_binding','direct_local_design_binding','project_rule_binding'},
}
WEAK_TYPES = {'manufacturer_generic','online_generic','layer_only','specification_only',
              'nearby_text','pattern_sample','candidate_confidence'}


def _pointer(document, pointer):
    if pointer == '': return document
    if not isinstance(pointer,str) or not pointer.startswith('/'):
        raise ValueError('Source assertion requires a JSON pointer')
    value=document
    for token in pointer[1:].split('/'):
        token=token.replace('~1','/').replace('~0','~')
        value=value[int(token)] if isinstance(value,list) else value[token]
    return value


def load_bundle(path):
    """Verify reviewed bindings; never infer semantic claims from source text."""
    path=Path(path).resolve()
    bundle=json.loads(path.read_text(encoding='utf-8-sig'))
    verified=[]
    for source in bundle.get('sources',[]):
        p=(path.parent/source['path']).resolve()
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != source['sha256'].lower(): raise ValueError('Project evidence source hash mismatch')
        document=json.loads(p.read_text(encoding='utf-8-sig'))
        for assertion in source.get('assertions',[]):
            if _pointer(document,assertion['pointer']) != assertion['expected']:
                raise ValueError('Project evidence source assertion mismatch')
        verified.append({'source_id':source['source_id'],'path':str(p),'sha256':digest,
                         'assertions':source.get('assertions',[])})
    ids=[s['source_id'] for s in verified]
    if len(set(ids))!=len(ids): raise ValueError('Duplicate source ids')
    for e in bundle.get('evidence',[]):
        refs=e.get('source_ids',[])
        if not refs or any(ref not in ids for ref in refs):
            raise ValueError('Every file-backed evidence record needs verified sources')
    bundle.setdefault('provenance',[]).extend(verified)
    bundle['provenance'].append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return bundle
