"""Offline CLI: resolve.py --rules FILE --request FILE --rule-id ID --output NEWFILE."""
import argparse
import json
from pathlib import Path
from rules import load_rules
from resolver import resolve

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ('rules','request','rule-id','output'):
        p.add_argument('--'+name, required=True)
    a=p.parse_args()
    rules=load_rules(a.rules, Path(__file__).resolve().parents[1])
    rule=next(r for r in rules if r['rule_id']==a.rule_id)
    result=resolve(rule,json.loads(Path(a.request).read_text(encoding='utf-8-sig')))
    with open(a.output,'x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
