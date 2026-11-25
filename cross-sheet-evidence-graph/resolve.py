"""Pinned local artifact -> exclusively created graph. No CAD access."""
import argparse
import hashlib
import json
from pathlib import Path
from graph import build_graph

def unique_pairs(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate JSON key: '+k)
        d[k]=v
    return d

def invalid_constant(value):raise ValueError('nonfinite JSON number: '+value)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();raw=Path(a.input).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.sha256:raise ValueError('input hash mismatch')
    document=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique_pairs,parse_constant=invalid_constant)
    result=build_graph(document,a.sha256)
    serialized=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    with Path(a.output).open('x',encoding='utf-8',newline='\n') as f:f.write(serialized)

if __name__=='__main__':main()
