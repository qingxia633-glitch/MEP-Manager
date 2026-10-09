using System;
using System.Linq;
using System.Collections.Generic;
namespace Mep.Routing {
 public class Segment { public string id, rawEntityRef, layer, systemScope; public double[] a,b; public int vertexIndex; public bool clippedA,clippedB; }
 public class Node { public string nodeId; public double[] point; public string modelType="RoutingNodeCandidate"; }
 public class Edge { public string edgeId,rawEntityRef,layer,fromNode,toNode; public double[] startXY,endXY; public double segmentLength; public int vertexIndex; public string modelType="RoutingEdgeCandidate",status="candidate",systemScope="fire_alarm"; }
 public class Contact { public string a,b,type; public double[] point; }
 public class Endpoint { public string nodeRef,edgeRef; public double[] coordinates; public string modelType="RoutingEndpointCandidate",status="open",possibleCause="unresolved"; }
 public class Gap { public string modelType="RoutingGapCandidate",fromNode,toNode,status="unresolved",possibleCause="unresolved"; public double distance; public bool bridgeAllowed=false; }
 public class Component { public string componentId; public string[] edgeRefs,nodeRefs,openEndpointRefs; public double total2DGeometricLength; public string systemScope="fire_alarm"; }
 public class Result { public List<Node> nodes=new List<Node>(); public List<Edge> edges=new List<Edge>(); public List<Contact> contacts=new List<Contact>(); public List<Endpoint> openEndpoints=new List<Endpoint>(); public List<Gap> gaps=new List<Gap>(); public List<Component> components=new List<Component>(); }
 public static class Graph {
  static double Cross(double x,double y,double u,double v){return x*v-y*u;}
  static double D(double[] a,double[] b){return Math.Sqrt(Math.Pow(a[0]-b[0],2)+Math.Pow(a[1]-b[1],2));}
  static double[] P(Segment s,double t){return new[]{s.a[0]+t*(s.b[0]-s.a[0]),s.a[1]+t*(s.b[1]-s.a[1]),s.a[2]+t*(s.b[2]-s.a[2])};}
  static double Param(double[] p,Segment s){double x=s.b[0]-s.a[0],y=s.b[1]-s.a[1]; return ((p[0]-s.a[0])*x+(p[1]-s.a[1])*y)/(x*x+y*y);}
  static bool On(double[] p,Segment s,double e,out double t){t=Param(p,s); if(t<0||t>1)return false;var q=P(s,t);return D(p,q)<=e&&Math.Abs(p[2]-q[2])<=e;}
  public static bool Inside(double[] p,double[][] ring,double e){bool yes=false;for(int i=0,j=ring.Length-1;i<ring.Length;j=i++) {var a=ring[j];var b=ring[i];var s=new Segment{a=a,b=b};double t;if(D(a,b)>0&&On(new[]{p[0],p[1],a[2]},s,e,out t))return true;if((a[1]>p[1])!=(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])yes=!yes;}return yes;}
  static bool Intersect(Segment s,Segment r,out double t,out double u){double x=s.b[0]-s.a[0],y=s.b[1]-s.a[1],v=r.b[0]-r.a[0],w=r.b[1]-r.a[1];double d=Cross(x,y,v,w);t=u=0;if(Math.Abs(d)<1e-12)return false;t=Cross(r.a[0]-s.a[0],r.a[1]-s.a[1],v,w)/d;u=Cross(r.a[0]-s.a[0],r.a[1]-s.a[1],x,y)/d;return t>=0&&t<=1&&u>=0&&u<=1;}
  public static Result Build(Segment[] input,double[][] ring,double tolerance,double gapSearchDistance){
   if(ring.Length<3||tolerance<=0||gapSearchDistance<0)throw new ArgumentException("Invalid geometry policy");
   var segments=new List<Segment>();
   foreach(var s in input){if(s.systemScope!="fire_alarm")continue;if(s.a.Length!=3||s.b.Length!=3||s.a.Concat(s.b).Any(v=>double.IsNaN(v)||double.IsInfinity(v)))throw new ArgumentException("Invalid coordinates");if(D(s.a,s.b)<=tolerance)continue;
    var cuts=new List<double>{0,1};for(int i=0;i<ring.Length;i++){double t,u;if(Intersect(s,new Segment{a=ring[i],b=ring[(i+1)%ring.Length]},out t,out u))cuts.Add(t);}
    var sorted=cuts.Distinct().OrderBy(v=>v).ToArray();for(int i=1;i<sorted.Length;i++){double a=sorted[i-1],b=sorted[i];if((b-a)*D(s.a,s.b)<=tolerance||!Inside(P(s,(a+b)/2),ring,tolerance))continue;segments.Add(new Segment{id=s.id+":"+i,rawEntityRef=s.rawEntityRef,layer=s.layer,systemScope=s.systemScope,vertexIndex=s.vertexIndex,a=P(s,a),b=P(s,b),clippedA=a>0,clippedB=b<1});}
   }
   var result=new Result();var split=segments.Select(s=>new List<double>{0,1}).ToArray();
   for(int i=0;i<segments.Count;i++)for(int j=i+1;j<segments.Count;j++){
    var a=segments[i];var b=segments[j]; if(Math.Max(a.a[0],a.b[0])+tolerance<Math.Min(b.a[0],b.b[0])||Math.Max(b.a[0],b.b[0])+tolerance<Math.Min(a.a[0],a.b[0])||Math.Max(a.a[1],a.b[1])+tolerance<Math.Min(b.a[1],b.b[1])||Math.Max(b.a[1],b.b[1])+tolerance<Math.Min(a.a[1],a.b[1]))continue;
    bool touched=false;foreach(double t0 in new[]{0.0,1.0}){double t;var p=P(a,t0);if(!(t0==0?a.clippedA:a.clippedB)&&On(p,b,tolerance,out t)){split[j].Add(t);touched=true;result.contacts.Add(new Contact{a=a.id,b=b.id,point=p,type=(t==0||t==1)?"endpoint_to_endpoint":"endpoint_on_segment"});}p=P(b,t0);if(!(t0==0?b.clippedA:b.clippedB)&&On(p,a,tolerance,out t)){split[i].Add(t);touched=true;result.contacts.Add(new Contact{a=b.id,b=a.id,point=p,type=(t==0||t==1)?"endpoint_to_endpoint":"endpoint_on_segment"});}}
    double x,y;if(!touched&&Intersect(a,b,out x,out y)&&Math.Abs(P(a,x)[2]-P(b,y)[2])<=tolerance)result.contacts.Add(new Contact{a=a.id,b=b.id,point=P(a,x),type="crossing_without_connection"});
   }
   // Only segment endpoints and admitted T contacts become nodes; interior crossings never do.
   var clipNodes=new HashSet<string>();
   Func<double[],bool,string> node=(p,clipped)=>{var old=clipped?null:result.nodes.FirstOrDefault(n=>!clipNodes.Contains(n.nodeId)&&D(n.point,p)<=tolerance&&Math.Abs(n.point[2]-p[2])<=tolerance);if(old!=null)return old.nodeId;var n0=new Node{nodeId="node:"+result.nodes.Count,point=p};result.nodes.Add(n0);if(clipped)clipNodes.Add(n0.nodeId);return n0.nodeId;};
   for(int i=0;i<segments.Count;i++){var s=segments[i];var ts=split[i].Distinct().OrderBy(v=>v).ToArray();for(int k=1;k<ts.Length;k++){var a=P(s,ts[k-1]);var b=P(s,ts[k]);if(D(a,b)<=tolerance)continue;result.edges.Add(new Edge{edgeId="edge:"+result.edges.Count,rawEntityRef=s.rawEntityRef,layer=s.layer,vertexIndex=s.vertexIndex,startXY=a,endXY=b,fromNode=node(a,s.clippedA&&ts[k-1]==0),toNode=node(b,s.clippedB&&ts[k]==1),segmentLength=D(a,b)});}}
   var adjacent=result.nodes.ToDictionary(n=>n.nodeId,n=>new List<Edge>());foreach(var edge in result.edges){adjacent[edge.fromNode].Add(edge);adjacent[edge.toNode].Add(edge);}foreach(var n in result.nodes)if(adjacent[n.nodeId].Count==1)result.openEndpoints.Add(new Endpoint{nodeRef=n.nodeId,edgeRef=adjacent[n.nodeId][0].edgeId,coordinates=n.point});
   var seen=new HashSet<string>();foreach(var n in result.nodes){if(!seen.Add(n.nodeId))continue;var queue=new Queue<string>();queue.Enqueue(n.nodeId);var ns=new List<string>();var es=new HashSet<string>();while(queue.Count>0){var id=queue.Dequeue();ns.Add(id);foreach(var edge in adjacent[id]){es.Add(edge.edgeId);var next=edge.fromNode==id?edge.toNode:edge.fromNode;if(seen.Add(next))queue.Enqueue(next);}}result.components.Add(new Component{componentId="component:"+result.components.Count,nodeRefs=ns.ToArray(),edgeRefs=es.ToArray(),openEndpointRefs=result.openEndpoints.Where(p=>ns.Contains(p.nodeRef)).Select(p=>p.nodeRef).ToArray(),total2DGeometricLength=result.edges.Where(e=>es.Contains(e.edgeId)).Sum(e=>e.segmentLength)});}
   // Near ends are recorded, never joined. Search radius is an explicit investigation limit.
   for(int i=0;i<result.openEndpoints.Count;i++)for(int j=i+1;j<result.openEndpoints.Count;j++){var a=result.openEndpoints[i];var b=result.openEndpoints[j];if(a.edgeRef==b.edgeRef||Math.Abs(a.coordinates[2]-b.coordinates[2])>tolerance)continue;double d=D(a.coordinates,b.coordinates);if(d>tolerance&&d<=gapSearchDistance)result.gaps.Add(new Gap{fromNode=a.nodeRef,toNode=b.nodeRef,distance=d});}
   return result;
  }
 }
}
