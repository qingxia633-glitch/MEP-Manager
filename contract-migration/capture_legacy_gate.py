"""Materialize the unchanged legacy callable input; do not supply missing fields."""
import copy
import json
from unittest.mock import patch
from migrate import load, source, package, save, sha, OUT

def capture():
    old=load('project-evidence-gate','tests/test_resolver.py')
    def record(candidate,bundle,context):
        return copy.deepcopy(dict(candidate=candidate,bundle=bundle,context=context))
    with patch.object(old,'evaluate_semantics',record):
        value=old.run(records=[old.evidence()])
    s=source('project-evidence-gate/tests/test_resolver.py','candidate/bundle/run')
    w=package('synthetic-gate-callable-retained',value,copy.deepcopy(value),s,'synthetic legacy/1',[s],
              status='legacy_incomplete',missing=['No source for full instance parent_path/scope'])
    w['new_schema_version']='synthetic legacy/1 (retained, not promoted)'
    w['migration_tool']={'name':'capture-legacy-gate/1','sha256':sha(__file__)}
    w['supersedes_inventory_marker']='synthetic-gate-legacy-incomplete'
    w=save(w)
    with (OUT/'supplemental-manifest.json').open('x',encoding='utf-8') as f:
        json.dump([{'target_fixture':w['target_fixture'],'record_hash':w['record_hash'],'status':w['status']}],f,indent=2)

if __name__=='__main__':capture()
