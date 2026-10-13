"""Offline discovery CLI. Exclusive output; no DWG or registry writes."""
import argparse,json
from pathlib import Path
from annotations import load_report
from discovery import discover

def discover_shadow(report, *, manifest=None, project_id=None, encoding='utf-8-sig',
                    xy_tolerance=.001, nearby_distance=1000):
 """Verified bytes entry; never accepts a caller-supplied context/verified flag."""
 if manifest is None:raise ValueError('Shadow manifest required')
 if not isinstance(report,(str,Path)):raise TypeError('Shadow requires a report path, not context JSON')
 if not isinstance(project_id,str) or not project_id.strip():raise ValueError('Shadow explicit nonblank project_id required')
 context=load_report(report,project_id,encoding=encoding,manifest=manifest)
 result=discover(context,xy_tolerance,nearby_distance)
 result['report_integrity']=context['report_integrity']
 result['execution_mode']='verified_shadow_discovery'
 identity=context['report_identity']
 eligible=(identity.get('acquisition_mode')=='ModelSpaceTopLevelAllLayers' and
           identity.get('model_space_top_level')=='included' and identity.get('nested_blocks')=='not expanded')
 result['acquisition_scope_status']='eligible' if eligible else 'not_eligible'
 result['shadow_evaluable']=eligible
 result['binding_count']=len(result['bindings'])
 result['zero_binding_reason']=None
 if not result['bindings']:
  if not eligible:reason='acquisition_scope_not_top_level'
  elif any(e['binding_status']=='conflicting' for e in result['evidence']):reason='ambiguous_or_conflicting_evidence'
  elif any(l['association_status']=='explicit' for e in result['evidence'] for l in e['leader_geometry']):reason='no_target_match'
  else:reason='no_supported_leader_evidence'
  result['zero_binding_reason']=reason
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser()
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument('--snapshot');g.add_argument('--context')
 p.add_argument('--output',required=True);p.add_argument('--xy-tolerance',type=float,required=True)
 p.add_argument('--nearby-distance',type=float,default=1000)
 p.add_argument('--shadow',action='store_true');p.add_argument('--manifest')
 p.add_argument('--encoding',default='utf-8-sig');p.add_argument('--project-id')
 a=p.parse_args()
 if a.shadow:
  if not a.snapshot:p.error('--shadow requires --snapshot; context JSON is not verified bytes')
  result=discover_shadow(a.snapshot,manifest=a.manifest,project_id=a.project_id,encoding=a.encoding,
                         xy_tolerance=a.xy_tolerance,nearby_distance=a.nearby_distance)
 else:
  context=load_report(a.snapshot,a.project_id,encoding=a.encoding,manifest=a.manifest) if a.snapshot else json.loads(Path(a.context).read_text(encoding='utf-8-sig'))
  result=discover(context,a.xy_tolerance,a.nearby_distance)
 with open(a.output,'x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
