"""Offline discovery CLI. Exclusive output; no DWG or registry writes."""
import argparse,json
from pathlib import Path
from annotations import load_report
from discovery import discover

if __name__=='__main__':
 p=argparse.ArgumentParser()
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument('--snapshot');g.add_argument('--context')
 p.add_argument('--output',required=True);p.add_argument('--xy-tolerance',type=float,required=True)
 p.add_argument('--nearby-distance',type=float,default=1000)
 a=p.parse_args()
 context=load_report(a.snapshot) if a.snapshot else json.loads(Path(a.context).read_text(encoding='utf-8-sig'))
 result=discover(context,a.xy_tolerance,a.nearby_distance)
 with open(a.output,'x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
