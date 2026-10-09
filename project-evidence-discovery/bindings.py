"""Geometry adapter: reuse existing nearest-segment implementation, no new connector."""
import importlib.util,math
from pathlib import Path

_path=Path(__file__).resolve().parents[1]/'geometry-connection/resolver.py'
_spec=importlib.util.spec_from_file_location('discovery_geometry_dependency',_path)
_geometry=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_geometry)

def valid_point(p):
 return isinstance(p,(list,tuple)) and len(p)==3 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in p)

def nearest(point,target):
 g=target.get('geometry',{});vs=g.get('vertices_wcs',[])
 if not valid_point(point) or not g.get('complete') or g.get('type') not in ('LINE','LWPOLYLINE'):
  return None
 if len(vs)<2 or not all(valid_point(v) for v in vs) or any(g.get('bulges',[])):
  return None
 if g.get('type')=='LWPOLYLINE' and len(g.get('bulges',[]))!=len(vs):
  return None
 pairs=list(zip(vs,vs[1:]))
 if g.get('closed'):pairs.append((vs[-1],vs[0]))
 choices=[]
 for a,b in pairs:
  q,t=_geometry._nearest_segment(point,a,b)
  choices.append({'point_wcs':q,'distance':math.dist(point[:2],q[:2]),'xyz_distance':math.dist(point,q),
                  'segment_parameter':t,'geometric_basis':'GeometryConnectionResolver._nearest_segment on actual straight segment'})
 return min(choices,key=lambda x:x['distance'])
