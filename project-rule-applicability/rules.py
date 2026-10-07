"""Load external rule files and verify their immutable source digests."""
import hashlib
import json
from pathlib import Path


def load_rules(path, repository_root):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    root = Path(repository_root).resolve()
    for source in data['sources']:
        p = (root / source['path']).resolve()
        if not p.is_relative_to(root) or hashlib.sha256(p.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('rule source hash mismatch: ' + source['path'])
    ids = [r['rule_id'] for r in data['rules']]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate rule identity')
    return data['rules']
