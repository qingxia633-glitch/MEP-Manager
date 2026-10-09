"""JSON CLI for offline endpoint/INSERT evidence resolution."""
import argparse
import json
from pathlib import Path
from resolver import DrawingContext, resolve_connection

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',required=True)
    p.add_argument('--project-id',help='Explicit project identity for downstream evidence composition')
    p.add_argument('--probe',action='append',default=[])
    p.add_argument('--edge',required=True)
    p.add_argument('--target',required=True)
    location=p.add_mutually_exclusive_group(required=True)
    location.add_argument('--endpoint-index',type=int,choices=[0,-1])
    location.add_argument('--endpoint',nargs=3,type=float)
    p.add_argument('--tolerance',required=True,type=float)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    if Path(a.output).exists() or Path(a.output).is_symlink():
        raise FileExistsError('Output already exists; evidence is append-only')
    ctx=DrawingContext.from_reports(a.snapshot,a.probe)
    ctx.project_id=a.project_id
    endpoint=a.endpoint
    if endpoint is None:
        edge=ctx.entities.get(a.edge,{})
        if edge.get('type') not in ('LINE','LWPOLYLINE') or not edge.get('vertices'):
            p.error('No readable source edge endpoint; explicit coordinates cannot replace source evidence')
        endpoint=edge['vertices'][a.endpoint_index]
    result=resolve_connection(a.edge,endpoint,a.target,ctx,a.tolerance)
    with Path(a.output).open('x',encoding='utf-8') as output:
        json.dump(result,output,ensure_ascii=False,indent=2)

if __name__=='__main__':main()
