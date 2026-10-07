"""Read-only integrity verification for structured quantity evidence bundles."""
import hashlib
import json
from pathlib import Path

def load_evidence(path):
    path=Path(path).resolve()
    bundle=json.loads(path.read_text(encoding='utf-8-sig'))
    sources={}
    for s in bundle.get('sources',[]):
        p=(path.parent/s['path']).resolve()
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if s['source_id'] in sources or digest!=s['sha256'].lower():
            raise ValueError('Duplicate source id or evidence hash mismatch')
        sources[s['source_id']]={'path':str(p),'sha256':digest}
    def visit(x):
        if isinstance(x,dict):
            if 'source_id' in x and x['source_id'] not in sources:
                raise ValueError('Unverified evidence source reference')
            for value in x.values():visit(value)
        elif isinstance(x,list):
            for value in x:visit(value)
    for obj in bundle['objects']:
        # Upstream Gate provenance has its own source-id namespace; consume it opaquely.
        for key,value in obj.items():
            if key!='semantic_gate':visit(value)
        obj['verified_sources']=sources
    return bundle
