"""Validate a structured evidence bundle without building quantities."""
import argparse
import json
from pathlib import Path
from evidence import load_evidence
from resolver import resolve_eligibility

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    args=p.parse_args()
    if Path(args.output).exists() or Path(args.output).is_symlink():
        raise FileExistsError('Output already exists; evidence is append-only')
    results=[resolve_eligibility(o) for o in load_evidence(args.input)['objects']]
    with Path(args.output).open('x',encoding='utf-8') as output:
        json.dump(results,output,ensure_ascii=False,indent=2)

if __name__=='__main__':main()
