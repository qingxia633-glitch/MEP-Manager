"""JSON CLI. Output creation is exclusive; never overwrite an artifact."""
import argparse
import json
from pathlib import Path
from builder import build, replay_validate

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['build','replay_validate'])
    parser.add_argument('plan')
    parser.add_argument('--registry',help='Complete normalized issued-quantity registry JSON array')
    parser.add_argument('--frozen',help='Normalized frozen object; use explicit legacy adapter if needed')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.mode=='build':
        r=build(read(args.plan),read(args.registry) if args.registry else None)
    else:
        if not args.frozen: parser.error('--frozen required for replay_validate')
        r=replay_validate(read(args.plan),read(args.frozen))
    with Path(args.output).open('x',encoding='utf-8') as stream:
        json.dump(r,stream,ensure_ascii=False,indent=2)
    return 0 if r['status'] in ('built','replay_matched') else 1

if __name__=='__main__': raise SystemExit(main())
