"""Read-only replay of the new resolver; exclusive-create evidence outputs."""
import hashlib
import json
from pathlib import Path
import sys

MODULE=Path(__file__).resolve().parents[1]
ROOT=MODULE.parent
sys.path.insert(0,str(MODULE))
from rules import load_rules
from resolver import resolve, to_gate_evidence

def emit(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)

if __name__=='__main__':
    output=ROOT/'outputs/project-rule-applicability-resolver-v01'
    rules=load_rules(MODULE/'fixtures/project-rules-v01.json',ROOT)
    summary={}
    for edge in ('13C9D','13CC7','13CF5'):
        request=json.loads((MODULE/f'fixtures/{edge}.json').read_text(encoding='utf-8'))
        selected=rules[:18] if edge!='13CF5' else rules[-1:]
        proposals=[resolve(r,request) for r in selected]
        emit(output/f'{edge}-proposals.json',proposals)
        if edge=='13CF5':
            emit(output/'golden-pending-gate-bundle.json',to_gate_evidence(proposals[0]))
            assert proposals[0]['applicability_status']=='applicable'
        else:
            assert proposals[0]['applicability_status']=='unresolved'
            assert not any(p['may_submit_to_project_gate'] for p in proposals)
        summary[edge]=[{k:p[k] for k in ('rule_id','applicability_status','may_submit_to_project_gate')} for p in proposals]
    emit(output/'project-replay.json',dict(results=summary,formal_gate_results_modified=False,quantities_generated=False))
