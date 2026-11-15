"""New-file-only v2 acquisition or pinned v1 migration."""
import argparse
import hashlib
import json
from pathlib import Path
from registry_v2 import build_registry, migrate_v1

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--input-map');g.add_argument('--v1-registry')
    p.add_argument('--v1-sha256');p.add_argument('--output',required=True)
    a=p.parse_args()
    if a.input_map:
        m=json.loads(Path(a.input_map).read_text(encoding='utf-8-sig'))
        result=build_registry(m['project_id'],m['inputs'])
    else:
        data=Path(a.v1_registry).read_bytes()
        if hashlib.sha256(data).hexdigest()!=a.v1_sha256:raise ValueError('v1 hash mismatch')
        result=migrate_v1(json.loads(data.decode('utf-8-sig')))
    with Path(a.output).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(result,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
