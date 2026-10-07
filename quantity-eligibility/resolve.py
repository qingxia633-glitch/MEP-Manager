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
    results=[resolve_eligibility(o) for o in load_evidence(args.input)['objects']]
    Path(args.output).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
