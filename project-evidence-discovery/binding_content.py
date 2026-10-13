"""Canonical binding content, separate from stable ID and runtime provenance."""
from copy import deepcopy

RUNTIME_FIELDS = frozenset({
    'provenance','source_provenance','path','report_path','report_sha256',
    'verified_report_sha256','report_integrity','snapshot_id','report_identity',
    'manifest','manifest_status','manifest_path','hash_status','report_file',
})

def canonical_content(value):
    if isinstance(value,dict):
        return {k:canonical_content(v) for k,v in value.items() if k not in RUNTIME_FIELDS}
    if isinstance(value,(list,tuple)):return [canonical_content(v) for v in value]
    return value

def consolidate_bindings(bindings):
    groups={}
    for binding in bindings:groups.setdefault(binding['binding_id'],[]).append(binding)
    result=[]
    for candidates in groups.values():
        selected=deepcopy(candidates[0])
        different=any(b['canonical_content']!=selected['canonical_content'] for b in candidates)
        if different:
            selected.update(binding_status='conflicting',diagnostics=['binding_conflict'],
                            conflicting_variants=deepcopy(candidates),canonical_content=None)
            for variant in selected['conflicting_variants']:
                variant['pre_conflict_status']=variant['binding_status']
                variant['binding_status']='conflicting'
        elif any(b['binding_status']=='conflicting' for b in candidates):
            selected.update(binding_status='conflicting',diagnostics=['binding_conflict'])
        for b in candidates[1:]:
            for source in b['provenance']:
                if source not in selected['provenance']:selected['provenance'].append(deepcopy(source))
        result.append(selected)
    return result
