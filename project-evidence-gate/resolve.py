"""Evaluate a structured candidate against reviewed project evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from evidence import load_bundle
from resolver import evaluate_semantics

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',required=True)
    p.add_argument('--evidence',required=True)
    p.add_argument('--project-id',required=True)
    p.add_argument('--drawing-ref',required=True)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    source=Path(args.candidate)
    candidate=json.loads(source.read_text(encoding='utf-8-sig'))
    result=evaluate_semantics(candidate,load_bundle(args.evidence),{'project_id':args.project_id,'drawing_ref':args.drawing_ref})
    result['provenance']['candidate_file']={'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
