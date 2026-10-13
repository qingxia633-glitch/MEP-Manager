"""Explicit opt-in verification of the isolated AutoCAD validation report.

Not a synthetic JSON unit test, not project semantic evidence.
Usage: python -B verify_real_leader_report.py REPORT --encoding cp936
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from annotations import load_report
from discovery import discover

def verify(report,encoding,manifest=None):
    if manifest is None:raise ValueError('Verified report manifest required')
    def require(condition,message):
        if not condition:raise ValueError(message)
    context=load_report(report,'independent-validation',encoding,manifest=manifest)
    require(context['entity_counts']=={'LINE':1,'MTEXT':1,'LEADER':1,'MULTILEADER':1},'Unexpected validation entities')
    classic=next(x for x in context['leaders'] if x['type']=='LEADER')
    multi=next(x for x in context['leaders'] if x['type']=='MULTILEADER')
    require(all(classic['validation'].values()),'Invalid classic leader evidence')
    require(classic['arrow_wcs']==[5.,0.,0.],'Unexpected arrow')
    result=discover(context)
    require(len(result['bindings'])==1,'Expected one candidate binding')
    binding=result['bindings'][0]
    require(binding['annotation_handle']==classic['annotation_handle'],'Annotation mismatch')
    require(binding['target_id']==context['targets'][0]['id'],'Target mismatch')
    require(binding['distance']==0,'Nonzero residual')
    require(multi['association_status']=='unresolved','MLEADER unexpectedly promoted')
    return {'classic_object_chain':'passed','mleader_binding':'unresolved',
            'project_support':'not_validated','report_provenance':context['provenance']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('report')
    parser.add_argument('--encoding',default='utf-8-sig');parser.add_argument('--manifest',required=True);args=parser.parse_args()
    print(json.dumps(verify(args.report,args.encoding,args.manifest),ensure_ascii=False,indent=2))
